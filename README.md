# BLUETTI Integration for Home Assistant

[🇬🇧 English](./README.md) | [🇳🇱 Dutch](./README_nl.md) |
[🇩🇪 German](./README_de.md) | [🇨🇳 Chinees](./README_zh.md)

The **BLUETTI Integration** is a built-in component of Home Assistant and is
officially supported by **BLUETTI**. It allows you to manage BLUETTI smart power
stations directly from Home Assistant.

## ✨ Features

- ✅ Inverter status
- ✅ Battery charge (SoC)
- ✅ AC switch
- ✅ DC switch
- ✅ Main switch
- ✅ AC ECO mode
- ✅ Operating mode selector: backup, self-consumption, peak/off-peak
- ✅ Disaster alert

## 🎮 Supported Power Station Models

> [!NOTE]
>
> In future versions, the BLUETTI Integration will be expanded to support
> additional new and existing power station models.

| Power Station Model | Inverter Status | Battery SoC | AC Switch | DC Switch | Main Switch | AC ECO | Mode Selector | Disaster Alert |
| :------------------ | :-------------: | :---------: | :-------: | :-------: | :---------: | -----: | :-----------: | :------------: |
| APEX300             |       ✅        |     ✅      |    ✅     |           |     ✅      |     ✅ |      ✅       |                |
| Elite100V2          |       ✅        |     ✅      |    ✅     |    ✅     |             |     ✅ |      ✅       |                |
| Elite30V2           |       ✅        |     ✅      |    ✅     |    ✅     |             |     ✅ |      ✅       |                |
| EP13K               |       ✅        |     ✅      |           |           |     ✅      |        |      ✅       |       ✅       |
| EP2000              |       ✅        |     ✅      |           |           |     ✅      |        |      ✅       |       ✅       |
| EP6K                |       ✅        |     ✅      |           |           |     ✅      |        |      ✅       |       ✅       |
| FP                  |       ✅        |     ✅      |    ✅     |           |     ✅      |     ✅ |      ✅       |       ✅       |

## 📦 Installing the BLUETTI Integration

### Home Assistant Operating System

Follow these steps to install the **BLUETTI Integration** in **Home Assistant**.

You can use the **Advanced SSH & Web Terminal** add-on or connect to your **Home
Assistant server** via **SSH**.

```bash
ssh username@host-ip
```

If you are running Home Assistant as a Docker container on **Windows**,
**macOS**, or **Linux**, first log in to the host machine (where Docker is
running):

```bash
ssh username@host-ip
```

Then open a shell in the Home Assistant container:

```bash
docker exec -it container-name /bin/bash
```

### Installation Steps

1. **Go to your Home Assistant configuration directory:**

   ```bash
   cd config 2>/dev/null || echo "You are already in the 'config' directory. Proceed with step 2."
   ```

2. **Create the `custom_components` folder** (if it does not exist):

   ```bash
   mkdir -pv custom_components
   ```

3. **Clone the BLUETTI Integration GitHub repository:**

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   mv /config/bluetti-home-assistant/custom_components/bluetti /config/custom_components/bluetti
   rm -r /config/bluetti-home-assistant
   ```

4. **Restart Home Assistant** to load the new integration:
   - For **Home Assistant Operating System**:

     ```bash
     ha core restart
     ```

   - For **Docker installations**:

     ```bash
     docker restart container-name
     ```

### Installation via Home Assistant Community Store (HACS)

The **BLUETTI Integration** is not yet available in the official
[HACS repository](https://github.com/hacs/integration). You need to add it
manually as a **custom repository**.

> [!NOTE]
>
> **What is HACS?** HACS (_Home Assistant Community Store_) is an extension for
> Home Assistant that works as an **app store** for third-party integrations.
> Make sure HACS is installed before adding custom repositories.

#### Installation Steps

1. Open **HACS → Integrations → Custom Repositories** (top right of the page).

2. Add the following repository and select the correct type:
   - **Repository:** [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **Type:** Integration

3. Go to **HACS → Integrations**. The **BLUETTI** integration will now appear in
   the list. Click to install.

4. **Restart Home Assistant** to complete the installation.

## ⚙️ Integration Configuration

1. Go to **_Settings → Devices & Services_** to open the list of integrations.
   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. Click **_Add Integration_**, search for **bluetti**, and select the **BLUETTI
   Integration** to start OAuth authorization.
   <img src="./doc/images/2-search_and_add_integration.png" width="880">

3. Grant **Home Assistant** permission to access your BLUETTI account and
   connect to the BLUETTI cloud service.
   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. Enter your BLUETTI account credentials to log in and authorize.
   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. Confirm that **Home Assistant** may link your BLUETTI account.
   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. Select the BLUETTI devices you want to use and manage in Home Assistant.
   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## ❓ Frequently Asked Questions (FAQ)

### **Question:** The BLUETTI Integration cannot be found after installation?

**Answer:** Check whether the `custom_components` folder is in the correct
location and restart Home Assistant.

### **Question:** The integration stays offline or cannot connect to the BLUETTI server?

**Answer:** Check your **network connection**, **port settings**, and
**firewall** to ensure **Home Assistant** can access BLUETTI power stations.

### **Question:** Does the BLUETTI Integration work locally?

**Answer:** Not yet. The BLUETTI Integration currently works via the cloud. A
local mode is under development but will take some time to complete.

## 🔄 Updating the BLUETTI Integration

### Home Assistant Operating System

1. **Update the BLUETTI Integration** (if needed):

   ```bash
   cd /config/custom_components/bluetti-home-assistant
   git pull
   ```

2. **Restart Home Assistant** to load the updated integration:
   - For **Home Assistant Operating System**:

     ```bash
     ha core restart
     ```

   - For **Docker installations**:

     ```bash
     docker restart container-name
     ```

### Home Assistant Community Store

Update the integration via the HACS management page.

## 📮 Support & Feedback

💬 Have questions, issues, or suggestions? Let us know via **GitHub Issues:**
[https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
