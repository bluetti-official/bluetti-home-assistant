# BLUETTI Integration für HomeAssistant

[English](./README.md) | [Deutsch](./README_de.md) | [简体中文](./README_zh.md)

Die BLUETTI Power Station Integration ist eine Komponente für Home Assistant, die von BLUETTI offiziell unterstützt wird. Mit dieser ist es möglich BLUETTI Smart Power Station-Geräte in Home Assistant verwenden.

Das GitHub-Repository der Integration ist: https://github.com/bluetti-official/bluetti-home-assistant.

# ✨ Funktionen

- ✅ Status des Wechselrichters 
- ✅ Batteriestand (SOC)
- ✅ AC Schalter  
- ✅ DC Schalter 
- ✅ Gerät ausschalten  
- ✅ AC ECO Modus
- ✅ Wechseln des Arbeitsmodus: Backup, Eigenverbrauch, Zeitsteuerung
- ✅ Unwetterwarnung 

# 🎮 Liste der unterstützen Geräte
> Hinweis: Mit der Zeit werden mehr Geräte dazukommen.

| Gerät   | Wechselrichter-Status | Batteriestand | AC Schalter | DC Schalter | Gerät ausschalten | AC ECO Modus | Arbeitsmodus wechseln | Unwetterwarnung |
|---------|------------------------|----------------|--------------|--------------|--------------------|----------------|------------------------|------------------|
| EP13K   | ✅                     | ✅             |              |              | ✅                |                | ✅                    | ✅               |
| EP6K    | ✅                     | ✅             |              |              | ✅                |                | ✅                    | ✅               |
| EP2000  | ✅                     | ✅             |              |              | ✅                |                | ✅                    | ✅               |
| FP      | ✅                     | ✅             | ✅           |              | ✅                | ✅             | ✅                    | ✅               |

# 📦 Integration Installation

Es gibt zwei Wege diese Integration zu installieren.

## Manuelle Installation

1. Öffne den `Home Assistant` Konfigurationsordner
```shell
$ cd /<ha workspaces>/core/config/custom_components
```
2. Klone das `BLUETTI Power Station Integration` Github Repository.
```shell
$ git clone https://github.com/bluetti-official/bluetti-home-assistant.git
```
3. ...oder lade den ZIP-Ordner herunter und entpacke den Inhalt in den "custom-integration" Ordner von `Home Assistant`:
```shell
$ unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
```
4. Starte dein `Home Assistant` System neu.

## Installation mit HACS

Die `BLUETTI Power Station Integration` wurde bisher nicht dem offiziellem HACS Repository hinzugefügt, diese muss manuell als benutzerdefiniertes Repository hinzugefügt werden. HACS selbst ist ein Home Assistant-Plugin (Benutzer müssen HACS zuerst installieren) und ähnelt einem App Store . Über diesen App Store können andere Integrationen von Drittanbietern installiert werden.

1. Befolgen Sie folgende Schritte: „HACS -> Integration -> Benutzerdefiniertes Repository (befindet sich in der oberen rechten Ecke der Seite)“.
2. Fügen Sie das Repository hinzu und wählen Sie den Typ aus:
   - Repository: https://github.com/bluetti-official/bluetti-home-assistant.git
   - Typauswahl/Art: Integration
3. Auf der Seite „Integration“ von HACS sehen Sie dann die Integration „BLUETTI“. Klicken Sie darauf, um sie zu installieren.
4. Starten Sie abschließend Ihr `Home Assistant`-System neu.

# ⚙️ Konfiguration

1. Befolgen Sie folgende Schritte: Klicken Sie auf „Einstellungen -> Geräte & Dienste“
   <img src="./doc/images/1-setting_devices_and_services.png" width="880">
2. Klicken Sie auf die Schaltfläche „Integration hinzufügen“ und suchen Sie dann nach dem Stichwort „bluetti“. Wählen Sie die Integration „BLUETTI“ aus, um mit der Anmeldung fortzufahren.  
   <img src="./doc/images/2-search_and_add_integration.png" width="880">
3. Sie müssen zustimmen, dass „Home Assistant“ auf Ihr BLUETTI-Konto zugreifen und eine Verbindung mit dem BLUETTI-Cloud-Dienst herstellen darf.  
   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">
4. Geben Sie Ihr BLUETTI-Konto ein, um die Anmeldung durchzuführen. Diese nutzen Sie z.B bereits in der Bluetti-App
   <img src="./doc/images/4-oauth_enter_bluetti_account.png">
5. Sie müssen zustimmen, dass „Home Assistant“ eine Verbindung zu Ihrem BLUETTI-Konto herstellt.  
   <img src="./doc/images/5-oauth_link_account_to_ha.png">
6. Wählen Sie Ihre BLUETTI-Geräte aus, die in Home Assistant verwendet und verwaltet werden sollen. Es werden nur bestimmte Geräte unterstützt.
   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">  
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

# ❓ FAQ

- **`BLUETTI Integration` wird nicht nach der Installation gefunden?**  
  Bitte überprüfen Sie, ob der Pfad `custom_components` korrekt ist, und vergewissern Sie sich, dass das System `Home Assistant` neu gestartet wurde.

- **Permanent offline oder Verbindung zu den Bluetti-Servern fehlgeschlagen?**  
  Bitte überprüfen Sie das Netzwerk, die Ports und die Firewall, um sicherzustellen, dass die `Home Assistant`-Integration auf die Geräte zugreifen kann.

- **Wie aktualiere ich die`BLUETTI Integration`?**  
  1) HACS aufrufen und Update durchführen
  2) Update mit `git`
```shell
$ cd /<ha workspaces>/config/custom_components/bluetti
$ git pull
```

# 📮 Unterstützung & Feedback

- GitHub Issues: https://github.com/bluetti-official/bluetti-home-assistant/issues
