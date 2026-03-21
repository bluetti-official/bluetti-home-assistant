# BLUETTI Integration für HomeAssistant

[🇨🇳 简体中文](./README_zh.md) | [🇩🇪 German](./README_de.md) | [🇬🇧 English](./README.md) | 
[🇳🇱 Dutch](./README_nl.md) | [🇺🇦 Ukrainian](./README_uk.md)

Die BLUETTI Power Station Integration ist eine Komponente für Home Assistant,
die von BLUETTI offiziell unterstützt wird. Mit dieser ist es möglich BLUETTI
Smart Power Station-Geräte in Home Assistant verwenden.

Das GitHub-Repository der Integration ist:
[https://github.com/bluetti-official/bluetti-home-assistant](https://github.com/bluetti-official/bluetti-home-assistant).

## ✨ Funktionen

- ✅ Status des Wechselrichters
- ✅ Batteriestand (SOC)
- ✅ AC Schalter
- ✅ DC Schalter
- ✅ Gerät ausschalten
- ✅ AC ECO Modus
- ✅ DC ECO Modus
- ✅ Wechseln des Arbeitsmodus: Backup, Eigenverbrauch, Zeitsteuerung
- ✅ Schlafmodus
- ✅ PV Eingangsleistung
- ✅ Net zeingangsleistung
- ✅ AC Ausgangsleistung
- ✅ DC Ausgangsleistung

## 🎮 Liste der unterstützen Geräte

> [!NOTE]
>
> Mit der Zeit werden mehr Geräte dazukommen.

|            Gerät             |               Firmenname                | Wechselrichter-Status | Batteriestand | AC Schalter | DC Schalter | Gerät ausschalten | AC ECO Modus | DC ECO Modus | Arbeitsmodus wechseln |   Schlafmodus   | PV-Eingangsleistung | Netzeingangsleistung | AC Ausgangsleistung | DC Ausgangsleistung |
|:----------------------------:|:---------------------------------------:|:---------------------:|:-------------:|:-----------:|:-----------:|:-----------------:|:------------:|:------------:|:---------------------:|:---------------:|:-------------------:|:--------------------:|:-------------------:|:-------------------:| 
|            AP300             |                Apex 300                 |                       |       ✅       |      ✅      |             |                   |      ✅       |              |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|            EL300             |           Elite 300,AORA 300            |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|        EL320,AORA320         |           Elite 320,AORA 320            |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|            EL400             |                Elite 400                |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|            EP13K             |                  EP13k                  |           ✅           |       ✅       |             |             |         ✅         |              |              |           ✅           |                 |                     |                      |                     |                     |
|            EP2000            |                  EP200                  |           ✅           |       ✅       |             |             |         ✅         |              |              |           ✅           |                 |                     |                      |                     |                     |
|             EP6K             |                  EP6k                   |           ✅           |       ✅       |             |             |         ✅         |              |              |           ✅           |                 |                     |                      |                     |                     |
|            EP760             |                  EP760                  |           ✅           |       ✅       |             |             |         ✅         |              |              |                       |                 |                     |                      |                     |                     |
|           EP500Pro           |                EP500Pro                 |                       |       ✅       |      ✅      |      ✅      |                   |              |              |           ✅           |                 |          ✅          |          ✅           |          ✅          |          ✅          |
|              FP              |             Fridge Product              |           ✅           |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |                     |                      |                     |                     |
|  PR100V2,EL100V2,AORA100V2   | Premium 100 V2,Elite 100 V2,AORA 100 V2 |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
| PR200V2,Elite 200 V2,AORA200 | Premium 200 V2,Elite 200 V2,AORA 200 V2 |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|        PR30V2,EL30V2         |  Premium 30 V2,Elite 30 V2,AORA 30 V2   |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|             RV5              |                   RV5                   |           ✅           |       ✅       |      ✅      |      ✅      |                   |              |              |           ✅           |        ✅        |          ✅          |          ✅           |          ✅          |          ✅          |
|      Balco260,Balco500       |            Balco260,Balco500            |           ✅           |       ✅       |      ✅      |             |                   |              |              |           ✅           |                 |          ✅          |          ✅           |          ✅          |                     |
|         AC300,AC500          |               AC300,AC500               |                       |       ✅       |      ✅      |      ✅      |                   |              |              |           ✅           |                 |          ✅          |          ✅           |          ✅          |          ✅          |
|        AC200PL,AC200L        |             AC200PL,AC200L              |                       |       ✅       |      ✅      |      ✅      |                   |      ✅       |      ✅       |           ✅           |                 |          ✅          |          ✅           |          ✅          |          ✅          |


## 📦 Integration Installation

Es gibt zwei Wege diese Integration zu installieren.

### Manuelle Installation

1. Öffne den `Home Assistant` Konfigurationsordner

   ```bash
   cd /<ha workspaces>/core/config/custom_components
   ```

2. Klone das `BLUETTI Power Station Integration` Github Repository.

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   ```

3. Oder lade den ZIP-Ordner herunter und entpacke den Inhalt in den
   "custom-integration" Ordner von `Home Assistant`:

   ```bash
   unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
   ```

4. Starte dein `Home Assistant` System neu.

### Installation mit HACS

Die `BLUETTI Power Station Integration` wurde bisher nicht dem offiziellem HACS
Repository hinzugefügt, diese muss manuell als benutzerdefiniertes Repository
hinzugefügt werden. HACS selbst ist ein Home Assistant-Plugin (Benutzer müssen
HACS zuerst installieren) und ähnelt einem App Store . Über diesen App Store
können andere Integrationen von Drittanbietern installiert werden.

1. Befolgen Sie folgende Schritte: „HACS -> Integration -> Benutzerdefiniertes
   Repository (befindet sich in der oberen rechten Ecke der Seite)“.

2. Fügen Sie das Repository hinzu und wählen Sie den Typ aus:
   - **Repository:**
     [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **Typauswahl/Art:** Integration

3. Auf der Seite „Integration“ von HACS sehen Sie dann die Integration
   „BLUETTI“. Klicken Sie darauf, um sie zu installieren.

4. Starten Sie abschließend Ihr `Home Assistant`-System neu.

## ⚙️ Konfiguration

1. Befolgen Sie folgende Schritte: Klicken Sie auf „Einstellungen -> Geräte &
   Dienste“

   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. Klicken Sie auf die Schaltfläche „Integration hinzufügen“ und suchen Sie dann
   nach dem Stichwort „bluetti“. Wählen Sie die Integration „BLUETTI“ aus, um
   mit der Anmeldung fortzufahren.

   <img src="./doc/images/2-search_and_add_integration.png" width="880">

3. Sie müssen zustimmen, dass „Home Assistant“ auf Ihr BLUETTI-Konto zugreifen
   und eine Verbindung mit dem BLUETTI-Cloud-Dienst herstellen darf.

   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. Geben Sie Ihr BLUETTI-Konto ein, um die Anmeldung durchzuführen. Diese nutzen
   Sie z.B bereits in der Bluetti-App

   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. Sie müssen zustimmen, dass „Home Assistant“ eine Verbindung zu Ihrem
   BLUETTI-Konto herstellt.

   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. Wählen Sie Ihre BLUETTI-Geräte aus, die in Home Assistant verwendet und
   verwaltet werden sollen. Es werden nur bestimmte Geräte unterstützt.

   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## ❓ FAQ

### `BLUETTI Integration` wird nicht nach der Installation gefunden?

Bitte überprüfen Sie, ob der Pfad `custom_components` korrekt ist, und
vergewissern Sie sich, dass das System `Home Assistant` neu gestartet wurde.

### Permanent offline oder Verbindung zu den Bluetti-Servern fehlgeschlagen?

Bitte überprüfen Sie das **Netzwerk**, die **Ports** und die **Firewall**, um
sicherzustellen, dass die `Home Assistant`-Integration auf die Geräte zugreifen
kann.

### Wie aktualiere ich die`BLUETTI Integration`?

1. HACS aufrufen und Update durchführen
2. Update mit `git`

   ```bash
   cd /<ha workspaces>/config/custom_components/bluetti
   git pull
   ```

## 📮 Unterstützung & Feedback

💬 Haben Sie Probleme oder Anregungen? Erstellen Sie ein Issue auf GitHub:
[https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
