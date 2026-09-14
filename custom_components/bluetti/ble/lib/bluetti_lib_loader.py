"""Loader for the pre-compiled Bluetti BLE shared library.

The BLE stack of this integration requires a platform-specific native
library (``_bluetti_ble_*.so``). This module provides the ``BleLibLoader``
class which locates an already-present copy or, when it is missing,
downloads the correct build from the official update server.

Expected file name
    _bluetti_ble_{os}_{arch}_{python}_{libc}_{compile_date}.so

    e.g. _bluetti_ble_linux_aarch64_313_musl_20260914.so

Download URL
    https://www.bluetti.com/ha/{compile_date}/{os}/{arch}-{python}-{libc}

The compile date is expressed as ``yyyyMMdd`` and is monotonically
increasing: only the current date is ever requested, an older one never is.

Usage::

    from custom_components.bluetti.ble.lib.loader import BleLibLoader

    loader = BleLibLoader()

    # Fast synchronous check.
    if (path := loader.get_lib_path()) is not None:
        ...

    # Asynchronous download with callback notification.
    await loader.ensure_bluetti_lib(on_downloaded=handle_downloaded)

    # Or block until the library is ready.
    path = await loader.ensure_bluetti_lib()
"""

from __future__ import annotations

import asyncio
import glob
import inspect
import logging
import os
import re
import sys
from typing import Any, Callable, Optional

from custom_components.bluetti.application_utils import EnvUtils
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

__all__ = ["BleLibLoader"]


class BleLibLoader:
    """Locate or download the platform-specific Bluetti BLE shared library.

    All implementation details are private; the public API consists of:

    * ``get_lib_path()`` -- synchronous fast path;
    * ``ensure_bluetti_lib(on_downloaded=None)`` -- async entry point;
    * ``download_lib(compile_date=None)`` -- explicit one-shot download;
    * ``cleanup_old_versions(keep_path)`` -- remove stale library files.
    """

    #: Bytes read from the network per chunk while streaming the download.
    _CHUNK_SIZE = 64 * 1024

    #: Flush downloaded chunks to disk after this many chunks.
    _WRITE_FLUSH_CHUNKS = 16

    _DEPENDENCY_MAP = {
        "linux_aarch64_musl": ["libcpsrt.so", "libmbedcrypto.so.3.6.4", "libmbedtls.so.3.6.4", "libmbedx509.so.3.6.4"],
        "linux_x86_64_gnu": ["libmbedcrypto.so.16", "libmbedtls.so.21", "libmbedx509.so.7"],
        "linux_x86_64_musl": ["libcpsrt.so", "libmbedcrypto.so.16", "libmbedtls.so.21", "libmbedx509.so.7"]
    }

    def __init__(
        self,
        lib_version: int,   # formatted as ``yyyyMMdd``
        oss_server: str,    # OSS file server
    ) -> None:
        """Create a loader.

        Args:
            lib_dir: Directory that holds (or will hold) the ``.so`` files.
                Defaults to the directory of this module.
            download_url_template: URL template using the same placeholders
                as :attr:`_DOWNLOAD_URL_TEMPLATE`. Falls back to the
                environment variable ``BLUETTI_BLE_DOWNLOAD_URL`` and then
                to the official update server.
        """
        self.os_type = EnvUtils.get_env_os_type()
        self.arch_type = EnvUtils.get_env_arch()
        self.libc_type = EnvUtils.get_env_libc_type()
        self.python_version = EnvUtils.get_env_python_version()

        # libs path
        self.dependency_lib_paths = []
        self.ble_lib_path = None

        self._oss_server = oss_server
        self._lib_version = lib_version
        self._lib_dir = os.path.dirname(os.path.abspath(__file__))
        self._lib_file_pattern: Optional[re.Pattern] = None
        self._download_url_template = "/ha-libs/" + str(self._lib_version) + "/{os}/{arch}_{python}_{libc}.so"
        self._download_lock: Optional[asyncio.Lock] = None
        self._download_task: Optional[asyncio.Task] = None


    # ------------------------------------------------------------------
    # Private: BLE naming / URL helpers
    # ------------------------------------------------------------------
    def _get_ble_lib_name(self) -> str:
        """Build the expected library file name for a given compile date."""
        return (
            f"_bluetti_ble_{self.os_type}_{self.arch_type}_"
            f"{self.python_version}_{self.libc_type}_"
            f"{str(self._lib_version)}.so"
        )

    def _get_ble_download_url(self) -> str:
        """Build the ble lib's download URL for ``compile_date``."""
        return (
            f"{self._oss_server}/ha-libs"
            f"/{str(self._lib_version)}"
            f"/{self.os_type}"
            f"/_bluetti_ble"
            f"_{self.os_type}_{self.arch_type}"
            f"_{self.python_version}_{self.libc_type}.so"
        )

    # ------------------------------------------------------------------
    # Private: download internals
    # ------------------------------------------------------------------
    @staticmethod
    def _remove_file(path: str) -> None:
        """Best-effort removal of a (possibly missing) file.

        Runs inside ``asyncio.to_thread`` so the event loop is never blocked.
        """
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            _LOGGER.warning("Could not remove file %s: %s", path, exc)

    @staticmethod
    def _write_chunks(path: str, chunks: list[bytes]) -> None:
        """Append downloaded chunks to ``path`` from a worker thread."""
        with open(path, "ab") as handle:
            for chunk in chunks:
                handle.write(chunk)

    async def _is_plausible_library(self, path: str) -> bool:
        """Cheap sanity check that a file looks like a real library.

        File access runs in a worker thread; Home Assistant flags blocking
        ``open()`` calls inside the event loop.
        """

        def _check() -> bool:
            try:
                if os.path.getsize(path) == 0:
                    return False
                if sys.platform.startswith("linux"):
                    with open(path, "rb") as handle:
                        return handle.read(4) == b"\x7fELF"
                return True
            except OSError:
                return False

        return await asyncio.to_thread(_check)

    async def _download_once(self, lib_filename: str, lib_url: str) -> Optional[str]:
        """Run the download + cleanup sequence exactly once (per instance).

        Serialized by an instance-level lock and re-checked, so concurrent
        callers never trigger more than one download.
        """
        if self._download_lock is None:
            self._download_lock = asyncio.Lock()
        async with self._download_lock:
            # Another caller may have finished the download while we waited.
            existing = await asyncio.to_thread(self.get_lib_path, lib_filename)
            if existing is not None:
                return existing

            lib_path = await self._download_lib(lib_url, None)
            if lib_path is not None:
                await asyncio.to_thread(self.cleanup_old_versions, lib_path)
            return lib_path

    async def _download_dependency_libs(self):
        lib_platform = self.os_type + "_" + self.arch_type + "_" + self.libc_type
        dependency_libs = self._DEPENDENCY_MAP[lib_platform]

        for lib_filename in dependency_libs:
            lib_path = await asyncio.to_thread(self.get_lib_path, lib_filename)
            if lib_path is not None:
                self.dependency_lib_paths.append(lib_path)
                continue

            lib_url = "/ha-libs/dependency/" + self.os_type + "/" + self.arch_type + "_" + self.libc_type + "/" + lib_filename
            lib_path = await self._download_once(lib_filename, lib_url)
            if lib_path is None:
                _LOGGER.error("Failed to download BLUETTI BLE dependency library from %s: %s", lib_platform, dependency_libs)
                continue

            self.dependency_lib_paths.append(lib_path)

        # print(self.dependency_lib_paths)

    async def _download_lib(self, lib_url: str, compile_date: Optional[int] = None) -> Optional[str]:
        """Download the library for ``compile_date`` (defaults to today).

        The payload is streamed into a ``.tmp`` file next to the final target
        and atomically moved into place afterwards, so an interrupted or
        failed download never leaves a corrupt ``.so`` behind.

        Returns the absolute path of the downloaded library, or ``None`` on
        failure.
        """
        try:
            import aiohttp  # Home Assistant core dependency; imported lazily.
        except ImportError as exc:
            _LOGGER.error("aiohttp is required to download the BLE library: %s", exc)
            return None

        if compile_date is None:
            url = self._oss_server + lib_url
            lib_path = os.path.join(self._lib_dir, os.path.basename(url))
        else:
            url = self._get_ble_download_url()
            lib_path = os.path.join(self._lib_dir, self._get_ble_lib_name())

        tmp_path = f"{lib_path}.tmp"
        _LOGGER.debug("Downloading BLE library from %s", url)

        try:
            # Remove a stale partial file from an earlier interrupted run.
            await asyncio.to_thread(self._remove_file, tmp_path)

            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to download BLE library: HTTP %s for %s",
                            response.status,
                            url,
                        )
                        return None
                    chunks: list[bytes] = []
                    async for chunk in response.content.iter_chunked(
                        self._CHUNK_SIZE
                    ):
                        chunks.append(chunk)
                        if len(chunks) >= self._WRITE_FLUSH_CHUNKS:
                            await asyncio.to_thread(
                                self._write_chunks, tmp_path, chunks
                            )
                            chunks.clear()
                    if chunks:
                        await asyncio.to_thread(self._write_chunks, tmp_path, chunks)

            if not await self._is_plausible_library(tmp_path):
                _LOGGER.error(
                    "Downloaded BLE library is not a valid library file: %s", url
                )
                await asyncio.to_thread(self._remove_file, tmp_path)
                return None

            await asyncio.to_thread(os.replace, tmp_path, lib_path)
            _LOGGER.info("BLE library downloaded to %s", lib_path)
            return lib_path
        except Exception as exc:
            _LOGGER.error("Failed to download BLE library from %s: %s", url, exc)
            await asyncio.to_thread(self._remove_file, tmp_path)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_lib_path(self, lib_filename: str) -> Optional[str]:
        """Return the path of an already-available library, or ``None``.

        Any build matching the current platform signature is accepted; when
        several are present the newest compile date wins and legacy files
        without a date suffix are treated as the oldest. This lets an
        already-downloaded (or pre-installed) library be reused without any
        network access.
        """

        try:
            entries = os.listdir(self._lib_dir)
        except OSError as exc:
            _LOGGER.warning("Cannot scan library directory %s: %s", self._lib_dir, exc)
            return None

        for name in entries:
            match = name.endswith(lib_filename)
            if not match:
                continue
            path = os.path.join(self._lib_dir, name)
            try:
                if not os.path.isfile(path) or os.path.getsize(path) == 0:
                    continue
            except OSError:
                continue

            return path

        return None

    async def download_ble_lib(self) -> Optional[str]:
        """Download the latest BLE library."""
        ble_lib_name = self._get_ble_lib_name()
        self.ble_lib_path = await self._download_lib(ble_lib_name, self._lib_version)
        return self.ble_lib_path

    def download_dependency_libs(self, haas: HomeAssistant):
        """Download the dependency libs of OS"""
        haas.async_create_task(asyncio.to_thread(asyncio.run, self._download_dependency_libs()), "bluetti-ble-libs-download")

    def cleanup_old_versions(self, keep_path: str) -> int:
        """Remove every other ``_bluetti_ble_*.so`` from the lib directory.

        Normally invoked automatically after a successful download; exposed
        as a public utility for manual maintenance. Any other file matching
        the bluetti library name belongs to an older build and is no longer
        needed.

        Returns the number of removed files.
        """
        removed = 0
        keep_path = os.path.abspath(keep_path)
        for old_path in glob.glob(os.path.join(self._lib_dir, "_bluetti_ble_*.so")):
            old_path = os.path.abspath(old_path)
            if old_path == keep_path:
                continue
            try:
                os.remove(old_path)
            except OSError as exc:
                _LOGGER.warning(
                    "Could not remove old BLE library %s: %s", old_path, exc
                )
                continue
            removed += 1
            _LOGGER.info("Removed old BLE library: %s", old_path)
        return removed
