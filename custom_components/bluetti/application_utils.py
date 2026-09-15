import ctypes
import platform
import sys


class EnvUtils:
    """Runtime Environment Utility"""

    # ------------------------------------------------------------------
    # platform fingerprint
    # ------------------------------------------------------------------
    @staticmethod
    def get_env_arch() -> str:
        """Return the normalized CPU architecture."""
        return platform.machine().lower()

    @staticmethod
    def get_env_os_type() -> str:
        """Return the normalized OS type used in file names and URLs."""
        return platform.system().lower()

    @staticmethod
    def get_env_python_version() -> int:
        """Return the interpreter version as ``major`` + ``minor`` (e.g. ``313``)."""
        py_version = int(f"{sys.version_info.major}{sys.version_info.minor}")
        if py_version < 313:
            py_version = 313
        elif py_version > 314:
            py_version = 314

        return py_version

    @staticmethod
    def get_env_libc_type() -> str:
        """Detect the libc implementation the interpreter runs against.

        Returns ``musl`` or ``gnu`` (``unknown`` on non-Linux platforms).
        """
        if not sys.platform.startswith("linux"):
            return "unknown"

        # glibc exports gnu_get_libc_version(); musl does not.
        try:
            libc = ctypes.CDLL(None)
            if hasattr(libc, "gnu_get_libc_version"):
                return "gnu"
            return "musl"
        except Exception:
            pass

        # Fallback: musl is mapped as libc.musl-*.so.1 on Alpine-like systems.
        try:
            with open("/proc/self/maps", "r", encoding="utf-8") as maps:
                if "libc.musl" in maps.read():
                    return "musl"
        except Exception:
            pass

        return "gnu"