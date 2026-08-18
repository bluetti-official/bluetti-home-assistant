# BLUETTI Integration for Home Assistant

[🇨🇳 简体中文](./README_zh.md) | [🇩🇪 German](./README_de.md) | [🇫🇷 Français](./README_fr.md) | [🇬🇧 English](./README.md) | 
[🇳🇱 Dutch](./README_nl.md) | [🇺🇦 Ukrainian](./README_uk.md)

BLUETTI Power Station Integration is an integrated component of Home Assistant
supported by BLUETTI official. It allows you to use BLUETTI smart Power Station
devices in Home Assistant.

The Integration's github repository is:
[https://github.com/bluetti-official/bluetti-home-assistant](https://github.com/bluetti-official/bluetti-home-assistant).

## ✨ Features

- ✅ Power Switch
- ✅ Inverter Status
- ✅ Battery state of charge (SOC)
- ✅ AC Switch
- ✅ DC Switch
- ✅ Main unit power switch
- ✅ AC ECO
- ✅ DC ECO
- ✅ Work mode switch: Backup, Self-consumption, Peak and Off-Peak
- ✅ Sleep Mode
- ✅ PV Input Power
- ✅ Grid Input Power
- ✅ AC Ouput Power
- ✅ DC Ouput Power

## 💡 Use Cases

- **Monitor your power station from anywhere** — battery level, inverter
  status and input/output power show up as regular Home Assistant sensors,
  so they work in dashboards, history graphs and the mobile app just like
  any other device.
- **Automate charging and discharging** — trigger automations based on
  battery state of charge (e.g. stop charging above 90%, send an alert
  below 20%).
- **Control AC/DC outputs remotely** — turn the power station's outputs on
  or off from Home Assistant, a script, or voice assistants integrated with
  Home Assistant.
- **Combine with energy dashboards** — use the power sensors (PV input,
  grid input, AC/DC output) alongside Home Assistant's Energy dashboard to
  track solar production and consumption.
- **React to grid/power events** — build automations that respond to the
  inverter or work-mode state, for example switching to backup mode when a
  power outage is detected elsewhere in your setup.

## 🎮 Power Station Support List

> [!NOTE]
>
> More power station models will be added in the future.

|     Power Station Model      |             Buesiness Name              | Inverter Status | Battery SOC | AC Switch | DC Switch | power switch | AC ECO | DC ECO | Work mode switch | Sleep Mode | PV Input Power | Grid Input Power | AC Output Power | DC Output Power | 
|:----------------------------:|:---------------------------------------:|:---------------:|:-----------:|:---------:|:---------:|:------------:|:------:|:------:|:----------------:|:----------:|:--------------:|:----------------:|:---------------:|:---------------:|
|            AP300             |                Apex 300                 |                 |      ✅      |     ✅     |           |             |   ✅    |        |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|            EL300             |           Elite 300,AORA 300            |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|        EL320,AORA320         |           Elite 320,AORA 320            |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|            EL400             |                Elite 400                |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|            EP13K             |                  EP13k                  |        ✅        |      ✅      |           |           |      ✅      |        |        |        ✅         |            |                |                  |                 |                 |
|            EP2000            |                  EP200                  |        ✅        |      ✅      |           |           |      ✅      |        |        |        ✅         |            |                |                  |                 |                 |
|             EP6K             |                  EP6k                   |        ✅        |      ✅      |           |           |      ✅      |        |        |        ✅         |            |                |                  |                 |                 |
|            EP760             |                  EP760                  |        ✅        |      ✅      |           |           |      ✅      |        |        |                  |            |                |                  |                 |                 |
|           EP500Pro           |                EP500Pro                 |                 |      ✅      |     ✅     |      ✅     |             |        |        |        ✅         |            |       ✅        |        ✅         |        ✅        |        ✅        |
|              FP              |             Fridge Product              |        ✅        |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |                |                  |                 |                 |
|  PR100V2,EL100V2,AORA100V2   | Premium 100 V2,Elite 100 V2,AORA 100 V2 |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
| PR200V2,Elite 200 V2,AORA200 | Premium 200 V2,Elite 200 V2,AORA 200 V2 |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|        PR30V2,EL30V2         |  Premium 30 V2,Elite 30 V2,AORA 30 V2   |                 |      ✅      |     ✅     |     ✅     |             |   ✅    |   ✅    |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|             RV5              |                   RV5                   |        ✅        |      ✅      |     ✅     |     ✅     |             |        |        |        ✅         |     ✅      |       ✅        |        ✅         |        ✅        |        ✅        |
|      Balco260,Balco500       |            Balco260,Balco500            |        ✅        |      ✅      |     ✅     |           |             |        |        |        ✅         |            |       ✅        |        ✅         |        ✅        |                 |
|         AC300,AC500          |               AC300,AC500               |                 |      ✅      |     ✅     |      ✅     |             |        |        |        ✅         |            |       ✅        |        ✅         |        ✅        |        ✅        |
|        AC200PL,AC200L        |             AC200PL,AC200L              |                 |      ✅      |     ✅     |      ✅     |             |   ✅    |   ✅    |        ✅         |            |       ✅        |        ✅         |        ✅        |        ✅        |


## 📦 Integration installation

There are two ways to install `BLUETTI Power Station Integration`.

### Install manually

1. Enter the `Home Assistant` configuration directory

   ```bash
   cd /<ha workspaces>/core/config/custom_components
   ```

2. Clone `BLUETTI Power Station Integration` github repository.

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   ```

3. Or download the integrated zip file and extract it to the custom integration
   directory of `Home Assistant`:

   ```bash
   unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
   ```

4. Reboot your `Home Assistant` system.

### Install by HACS

`BLUETTI Power Station Integration` hasn't been submitted to the default HACS
repository list yet, so for now it has to be added as a **custom repository**
(the repository already meets HACS's technical requirements for default
inclusion - `hacs.json`, a passing `hassfest`/HACS validation workflow,
tagged releases - submission to the default list is a step only this
repository's maintainers can take). HACS itself is a Home Assistant plugin
(users need to install HACS first), similar to an app store. Through this app
store, other third-party integrations can be installed.

1. Follow the steps "HACS -> Integration -> Custom Repository (it is in the
   upper right corner of the page)".

2. Add repository and make the type selection:
   - **Repository**:
     [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **Type:** Integration

3. Then, on the "Integration" page of HACS, you can see the `BLUETTI`
   Integration. Click to install.

4. Finally, Reboot your `Home Assistant` system.

## ⚙️ Integration configuration

1. Follow the steps "Settings -> Devices & services", click to enter the
   `Integration List` page.

   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. Click the "Add Integration" button, then search for the brand keyword
   `bluetti`; select the `BLUETTI` integration to proceed with the OAUTH
   authorization login.

   <img src="./doc/images/2-search_and_add_integration.png" width="880">

   You'll be asked to pick an authentication method: **Global (default)**
   works for most users. Pick **US** or **EU** only if you're affected by
   the login/"OAuth Expired" issues described in the FAQ below - most
   European (and specifically German) accounts should stay on **Global**
   unless they actually hit one of those symptoms.

3. You must agree that `Home Assistant` can access your BLUETTI account and
   establish a connection with the BLUETTI cloud service.

   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. Enter your BLUETTI account to authorize and login.

   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. You must agree that `Home Assistant` link to your BLUETTI account.

   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. Select your BLUETTI power station devices that need to be used and managed in
   Home Assistant.

   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## 🔄 How Data Is Updated

This integration is cloud-based: it talks to the BLUETTI cloud service, not
directly to your power station over the local network.

- **Push updates**: the integration keeps a WebSocket connection open to the
  BLUETTI cloud. When your power station reports a change (e.g. you toggle
  a switch in the official BLUETTI app), Home Assistant is notified and
  refreshes that device's entities within a few seconds.
- **Polling fallback**: independently of push updates, each device is also
  polled every 30 seconds. This guarantees entities stay up to date even if
  a push notification is missed.
- **Availability**: if the BLUETTI cloud is unreachable or your account's
  authorization expires, affected entities are marked `unavailable` in Home
  Assistant rather than showing stale data.

## 🧩 Example Automations

Replace `sensor.xxx_battery_level` / `switch.xxx_ac_output` with the actual
entity IDs created for your device (visible on the device page under
**Settings -> Devices & services -> BLUETTI**).

**Notify when the battery is low:**

```yaml
automation:
  - alias: "BLUETTI: notify on low battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.xxx_battery_level
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "BLUETTI power station battery is below 20%."
```

**Turn off the AC output at night:**

```yaml
automation:
  - alias: "BLUETTI: turn off AC output at night"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.xxx_ac_output
```

## 🗑️ Removing the Integration

1. Go to **Settings -> Devices & services**, open the `BLUETTI` integration
   card, click the three-dot menu on the integration entry and select
   **Delete**. This removes the config entry, its devices and entities from
   `Home Assistant`.

2. Remove the integration files:

   - **Installed via HACS**: go to **HACS -> Integrations**, open `BLUETTI`,
     and select **Remove**.
   - **Installed manually**: delete the `custom_components/bluetti` folder
     from your `Home Assistant` configuration directory.

3. Restart `Home Assistant` to complete the removal.

4. (Optional) If you no longer want `Home Assistant` to have access to your
   BLUETTI account, revoke it from your BLUETTI account's connected-apps
   settings.

## ❓ Frequently Asked Questions (FAQ)

### Not found `BLUETTI Integration` after installation?

Please check whether the `custom_components` path is correct and confirm whether
the `Home Assistant` system has been restarted.

### Always offline or failed connect to BLUETTI server?

Please check the **network**, **ports** and **firewall** to ensure that
`Home Assistant` can access the power station devices.

### How to update the `BLUETTI Integration`?

1. Enter the HACS management page to perform the update.
2. Update using `git`

   ```bash
   cd /<ha workspaces>/config/custom_components/bluetti
   git pull
   ```

### Getting "OAuth Expired" messages every few minutes, even though the integration still works?

This is usually caused by your traffic being geo-resolved to the wrong
BLUETTI cloud region (commonly affects users in Europe, whose requests can
land on US-designated nodes that don't recognize a token issued by the
correct regional node). See
[issue #121](https://github.com/bluetti-official/bluetti-home-assistant/issues/121).

To fix it, re-add the integration and pick **US** on the "Pick
authentication method" screen instead of the default:

1. Remove the `BLUETTI` integration (see the "Removing the Integration"
   section above — you only need step 1, not the file removal).
2. Add the integration again (**Settings -> Devices & services -> Add
   Integration -> BLUETTI**).
3. On the "Pick authentication method" screen, select **US** instead of
   **Global (default)**, then log in and re-select your devices.

If that screen only shows one option, update to a version of this
integration that includes the region picker.

### Can't log in at all, or "OAuth Expired" keeps coming back after switching to US - I'm in Europe/Germany?

Some EU accounts (reported in
[issue #72](https://github.com/bluetti-official/bluetti-home-assistant/issues/72))
can log in fine, but the *data* connection afterward keeps failing,
because the account's login endpoint is unaffected but its assigned data
gateway differs from the global default. This is a separate cause from
the US-routing issue above — trying **US** won't fix it, since the US
implementation changes the login endpoint too, which isn't the actual
problem here.

To fix it, follow the same steps as above, but select **EU** instead of
**US** on the "Pick authentication method" screen.

If neither **US** nor **EU** fixes it for your account, please open an
issue with your BLUETTI account's country/region so the correct gateway
can be identified.

## ⚠️ Known Limitations

- **Cloud-dependent**: this integration relies on the BLUETTI cloud service
  (OAuth2 login + WebSocket push). It does not work with BLUETTI power
  stations over the local network, and stops updating if BLUETTI's cloud
  service is unreachable.
- **One BLUETTI account per Home Assistant install**: all devices from a
  given BLUETTI account are grouped under a single integration entry. If
  you have devices on multiple BLUETTI accounts, only the most recently
  authenticated account's devices merge into that entry.
- **Newly bound devices require a manual step**: after binding a new device
  to your BLUETTI account, use **Settings -> Devices & services -> BLUETTI
  -> Configure** to add it — it is not picked up automatically.
- **Sensor coverage varies by model**: not every fn_code/sensor reported by
  every power station model is mapped to a Home Assistant entity yet. If a
  sensor is missing for your model, please open an issue.
- **Balco260 self-consumption mode** needs the electricity meter connected
  to report correctly.

## 📮 Support & Feedback

💬 Have any problems or suggestions? Create an issue on GitHub:
[https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
