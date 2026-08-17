# 1.1.0 2026-08-14
New:
- Pick your BLUETTI cloud region (Global / US / EU) when adding the integration, to fix login failures and repeated "OAuth Expired" notifications caused by your network being geo-routed to the wrong regional server.
- Add more devices to an existing setup later without logging in again, via Settings -> Devices & services -> BLUETTI -> Configure.
- Diagnostics download for troubleshooting, from the integration's device page.
- Every power (W) sensor - PV input, battery charge/discharge, grid input, AC/DC output, etc., on any supported model - now also gets a companion cumulated energy (kWh) sensor automatically, computed the same way as a manually added "Integral - Riemann sum" helper. No more setting up helpers by hand to use these values in the Energy dashboard.
- On models that don't report battery charge/discharge power directly (e.g. Balco260), an estimated battery charge power and discharge power sensor (and their kWh companions) are now added automatically, computed from the PV/grid/AC load balance. Clearly labeled "(Estimated)" since it's a power-balance approximation, not a real measurement.
- Diagnostics now also include each sensor's recognized type, to make it possible to tell "this data isn't sent by the cloud for my device" apart from "this data is sent but silently skipped" without digging through logs.

Fixes:
- Fix the integration disappearing after a Home Assistant restart when adding a device for the first time.
- Fix a control showing the device's serial number instead of its real name.
- Fix a recurring "OAuth Expired" notification caused by a token-refresh timer leak that could accumulate duplicate timers on every reload.
- Fix the cloud reporting a token as expired never actually attempting an automatic refresh - it only showed the "OAuth Expired" notification and required a manual reconfigure every time, even when the still-valid refresh token would have silently fixed it (#75, #81, #97).
- Fix an unrecognized sensor type crashing the whole integration setup instead of just skipping that sensor.
- Fix a blocking call, a websocket thread that could die silently without reconnecting, and several other reliability issues found during a full code review.

Internal:
- Adopted Home Assistant's DataUpdateCoordinator pattern for polling and push updates.
- Reached Home Assistant's "Gold" integration quality scale.
- Added a full automated test suite (100% line coverage).


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