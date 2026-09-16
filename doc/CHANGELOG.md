# 1.0.5 2026-09-16

## ✨What’s new
- Add ESPHome bluetooth proxy support
- Added cloud functionality support for the **Hub A1** device
- The BLE communication library support has been further improved, with added support for the **x86_64 musl** platform. Detailed platform support is as follows:
	- **Python 3.13 and below (HAOS ≤ 2026.2)**
		- linux_aarch64_musl: ✔️
		- linux_x86_64_gnu: &nbsp;&nbsp;&nbsp;✔️
		- linux_x86_64_musl: &nbsp;&nbsp;✔️（untested — no physical device available）
	- **Python 3.14 and above (HAOS ≥ 2026.3)**
		- linux_aarch64_musl: ✔️（untested — no physical device available）
		- linux_x86_64_gnu: &nbsp;&nbsp;&nbsp;✔️
		- linux_x86_64_musl: &nbsp;&nbsp;✔️

## 🚀Improvements
- Optimized the distribution of the BLE communication library: it is **no longer bundled with the source code**, which significantly reduces the size of the release package. When loading, the latest version of the integration will actively download the platform-appropriate library file from the server. If your HAOS has no Internet access, you can manually download it from [https://download.bluetti.app/ha-libs/](https://download.bluetti.app/ha-libs/) and place it in the `custom_components/bluetti/ble/lib` directory.
- Starting from **v1.3.0**, [BLUETTI Integration for Home Assistant (Community Edition)](https://github.com/bluetti-community/bluetti-home-assistant) also supports receiving real-time messages via WebSocket.

## 🐞Bug fixes
- [[#153](https://github.com/bluetti-official/bluetti-home-assistant/issues/153 "#153")] Fixed an issue where the ble can not work on the x86_64-musl platform.
- [[#154](https://github.com/bluetti-official/bluetti-home-assistant/issues/154 "#154")] Fixed an issue where the integration can't get bluetooth name when use ESPHome bluetooth proxy
- [[#158](https://github.com/bluetti-official/bluetti-home-assistant/issues/158 "#158")] Fixed an issue where the libc check don't work on the musl platform.
- [[#165](https://github.com/bluetti-official/bluetti-home-assistant/issues/165 "#165")] Fixed an issue where the WebSocket reported "Connection lost -goodbye" erery 2 minutes.

## ✨What’s new
- Add Ble support on x86_64 musl platform
- Add ESPHome bluetooth proxy support
- Add Python 3.14 support

# 1.0.4 2026-09-02

## 🐞Bug fixes
- [[#148](https://github.com/bluetti-official/bluetti-home-assistant/issues/148 "#148")] Fixed an issue where the integration did not work on linux-x86_64-musl platform.
- [[#149](https://github.com/bluetti-official/bluetti-home-assistant/issues/149 "#149")] Fixed an issue where the WebSocket always uses `ws://` scheme.

# 1.0.3 2026-08-31

> ℹ️ This version (1.0.3) has made significant changes to the OAuth access token. It is recommended to remove the BLUETTI integration and add it again. If you do not reconfigure the integration, you will not receive real-time device messages from the BLUETTI cloud.  
> ℹ️ It is recommended to connect a maximum of 3 Bluetooth devices at the same time.

## ✨What’s new
- Add French translation and README. Thanks [@chpego](https://github.com/chpego).
- Implement BLE controller mode for most devices for [#5](https://github.com/bluetti-official/bluetti-home-assistant/issues/5 "#5"), which supports three platforms: x86, ARM and Raspberry Pi.
- New models support for EB3A, AORA200V2, AP200, and AP300V2.
- Split "Grid Input Power" into "Grid Import Power" and "Grid Export Power".

## 🚀Improvements
- On OAuth login, return the optimal cloud endpoint for the account to reduce “OAuth expired” errors when accessing the cloud across regions. Endpoint selection depends on the account’s registration country—please ensure it is set correctly. Ideally, the registration country matches the country where the energy storage device is located.
- Negotiate the WebSocket heartbeat interval with the cloud. The default interval is changed from 10s to 60s. The heartbeat task now starts only after a `CONNECTED` response is received from the cloud.
- Implemented stricter authorization checks for real-time device message subscriptions, ensuring each account can only access messages from devices it is authorized to manage. This hardening was identified and resolved proactively during our internal security review. No user data was affected, and no action is required from users.

## 🐞Bug fixes
- Fixed an issue where the integration did not attempt a token refresh when the cloud reported that the token had expired.
- Fixed an issue where the cloud did not return a new refresh token when a token refresh was attempted.
- Fixed an issue where the WebSocket real-time messages could be occasionally lost in cluster deployments.

# 1.0.2 2026-03-31
New power station models have been supported:

- EP500Pro
- AORA300
- AORA30V2
- RV5
- Balco 260,Balco 500
- AC300,AC500
- AC200PL,AC200L

Functions changes are as follows:
- Add "PV Input Power", "Grid Input Power", "AC Ouput Power" and "DC Ouput Power", only some specific models are supported.
- Fix token expired can`t auto refesh issue.


# 1.0.1 2025-12-15
New power station models have been supported:

- AP300
- EL300
- EL320, AORA320
- PR30V2, EL30V2
- EL400
- EP760
- PR100V2, EL100V2, AORA100V2
- PR200V2, Elite 200 V2, AORA200

Functions changes are as follows:

- Add "DC ECO", only some specific models are supported.
- Add "Sleep Mode"
- Remove "Disaster Warning"

# 1.0.0 2025-10-17
The first version of BLUETTI Integration for Home Assistant.  
BLUETTI Power Station Support List:

- EP6K
- EP13K
- EP2000
- FP