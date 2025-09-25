# BLUETTI Integration for Home Assistant

[English](./README.md) | [简体中文](./README_zh.md)

BLUETTI Power Station Integration is an integrated component of Home Assistant supported by BLUETTI official. It allows you to use BLUETTI smart Power Station devices in Home Assistant.

The Integration's github repository is: https://github.com/bluetti-official/bluetti-home-assistant.

# ✨ Features

- ✅ Inverter Status  
- ✅ Battery state of charge (SOC)  
- ✅ Estimated battery life
- ✅ AC/DC ECO 
- ✅ AC/DC Switch  
- ✅ Main unit power switch  
- ✅ Work mode switch: 自发自用，备用电源，削峰填谷 
- ✅ Disaster Warning 

# 🎮 Power Station Support List
> tips: More power station models will be added successively in the future.

|        | Inverter Status | Battery SOC | Estimated battery life  | AC/DC ECO | AC/DC Switch | power switch | Work mode switch | Disaster Warning |
|--------|-----------------|-------------|-------------------------|-----------|--------------|--------------|------------------|------------------|
| EP13K  | ✅              | ✅         | ✅                      |           |              | ✅          | ✅               | ✅               |
| EP6K   | ✅              | ✅         | ✅                      |           |              | ✅          | ✅               | ✅               |
| EP2000 | ✅              | ✅         | ✅                      |           |              | ✅          | ✅               | ✅               |
| FP     | ✅              | ✅         | ✅                      | ✅        | ✅          | ✅          | ✅               | ✅               |

# 📦 Integration installation

There are two ways to install `BLUETTI Power Station Integration`.

## Install manually

1. Enter the `Home Assistant` configuration directory
```shell
$ cd /<ha workspaces>/core/config/custom_components
```
2. Clone `BLUETTI Power Station Integration` github repository.
```shell
$ git clone https://github.com/bluetti-official/bluetti-home-assistant.git
```
3. Or download the integrated zip file and extract it to the custom integration directory of `Home Assistant`:
```shell
$ unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
```
4. Reboot your `Home Assistant` system.

## Install by HACS

As the `BLUETTI Power Station Integration` has not yet been submitted to the official HACS repository, it is necessary to manually add a custom repository. HACS itself is a Home Assistant plugin (users need to install HACS first), similar to an app store. Through this app store, other third-party integrations can be installed.

1. Follow the steps "HACS -> Integration -> Custom Repository (it is in the upper right corner of the page)".
2. Add repository and make the type selection:
   - repository: https://github.com/bluetti-official/bluetti-home-assistant.git
   - type selection: Integration
3. Then, on the "Integration" page of HACS, you can see the `BLUETTI` Integration. Click to install.
4. Finally, Reboot your `Home Assistant` system.

# ⚙️ Integration configuration

1. Follow the steps "Settings -> Devices & services", click to enter the `Integration List` page.   
   <img src="./doc/images/1-setting_devices_and_services.png">