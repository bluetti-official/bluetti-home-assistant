# BLUETTI-Integration für Home Assistant

[🇬🇧 Englisch](./README.md) | [🇳🇱 Niederländisch](./README_nl.md) |
[🇩🇪 Deutsch](./README_de.md) | [🇨🇳 Chinesisch](./README_zh.md)

Die **BLUETTI-Integration** ist eine integrierte Komponente von Home Assistant
und wird offiziell von **BLUETTI** unterstützt. Sie ermöglicht es dir,
intelligente BLUETTI-Powerstations direkt in Home Assistant zu verwalten.

## ✨ Funktionen

- ✅ Status des Wechselrichters
- ✅ Batterieladung (SoC)
- ✅ AC-Schalter
- ✅ DC-Schalter
- ✅ Hauptschalter
- ✅ AC-ECO-Modus
- ✅ Betriebsmodus-Schalter: Notstrom, Eigenverbrauch, Spitzen- und
  Schwachlastzeiten
- ✅ Katastrophenwarnung

## 🎮 Unterstützte Powerstation-Modelle

> [!NOTE]
>
> In zukünftigen Versionen wird die BLUETTI-Integration um die Unterstützung
> zusätzlicher neuer und bestehender Powerstation-Modelle erweitert.

| Powerstation-Modell | Wechselrichterstatus | Batterie-SoC | AC-Schalter | DC-Schalter | Hauptschalter | AC ECO | Modusschalter | Katastrophenwarnung |
| :------------------ | :------------------: | :----------: | :---------: | :---------: | :-----------: | -----: | :-----------: | :-----------------: |
| APEX300             |          ✅          |      ✅      |     ✅      |             |      ✅       |     ✅ |      ✅       |                     |
| Elite100V2          |          ✅          |      ✅      |     ✅      |     ✅      |               |     ✅ |      ✅       |                     |
| Elite30V2           |          ✅          |      ✅      |     ✅      |     ✅      |               |     ✅ |      ✅       |                     |
| EP13K               |          ✅          |      ✅      |             |             |      ✅       |        |      ✅       |         ✅          |
| EP2000              |          ✅          |      ✅      |             |             |      ✅       |        |      ✅       |         ✅          |
| EP6K                |          ✅          |      ✅      |             |             |      ✅       |        |      ✅       |         ✅          |
| FP                  |          ✅          |      ✅      |     ✅      |             |      ✅       |     ✅ |      ✅       |         ✅          |

## 📦 Installation der BLUETTI-Integration

### Home Assistant Operating System

Befolge die folgenden Schritte, um die **BLUETTI-Integration** in **Home
Assistant** zu installieren.

Du kannst entweder das **Advanced SSH & Web Terminal**-Add-on verwenden oder
dich über **SSH** mit deinem **Home Assistant-Server** verbinden.

```bash
ssh benutzername@ip-adresse-des-hosts
```

Verwendest du Home Assistant als Docker-Container unter **Windows**, **macOS**
oder **Linux**? Dann melde dich zuerst auf dem Host an (dem Computer, auf dem
Docker läuft):

```bash
ssh benutzername@ip-adresse-des-hosts
```

Öffne anschließend eine Shell im Home Assistant-Container:

```bash
docker exec -it container-name /bin/bash
```

### Installationsschritte

1. **Wechsle in das Konfigurationsverzeichnis von Home Assistant:**

   ```bash
   cd config/
   ```

2. **Erstelle den Ordner `custom_components`**, falls dieser noch nicht
   existiert:

   ```bash
   mkdir -pv custom_components
   ```

3. **Klon die GitHub-Repository der BLUETTI-Integration:**

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   mv /config/bluetti-home-assistant/custom_components/bluetti /config/custom_components/bluetti
   rm -r /config/bluetti-home-assistant
   ```

4. **Starte Home Assistant neu**, um die neue Integration zu laden:
   - Für **Home Assistant Operating System**:

     ```bash
     ha core restart
     ```

   - Für **Docker-Installationen**:

     ```bash
     docker restart container-name
     ```

### Installation über Home Assistant Community Store (HACS)

Die **BLUETTI-Integration** ist noch nicht im offiziellen
[HACS-Repository](https://github.com/hacs/integration) enthalten. Daher musst du
sie manuell als **benutzerdefiniertes Repository** hinzufügen.

> [!NOTE]
>
> **Was ist HACS?** HACS (_Home Assistant Community Store_) ist eine Erweiterung
> für Home Assistant, die als **App Store** für Integrationen von Drittanbietern
> dient. Stelle sicher, dass HACS installiert ist, bevor du benutzerdefinierte
> Repositories hinzufügst.

#### Installationsschritte

1. Öffne **HACS → Integrationen → Benutzerdefinierte Repositories** (oben rechts
   auf der Seite).

2. Füge das folgende Repository hinzu und wähle den richtigen Typ aus:
   - **Repository:** [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **Typ:** Integration

3. Gehe anschließend zu **HACS → Integrationen**. Die **BLUETTI** integration
   erscheint nun in der Liste. Klicke darauf, um sie zu installieren.

4. **Starte Home Assistant neu**, um die Installation abzuschließen.

## ⚙️ Konfiguration der Integration

1. Gehe zu **_Einstellungen → Geräte & Dienste_**, um die Liste der
   Integrationen zu öffnen.
   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. Klicke auf **_Integration hinzufügen_**, suche nach **bluetti** und wähle die
   **BLUETTI-Integration** aus, um die OAuth-Autorisierung zu starten.
   <img src="./doc/images/2-search_and_add_integration.png" width="880">

3. Erteile **Home Assistant** die Berechtigung, auf dein BLUETTI-Konto
   zuzugreifen und eine Verbindung zum BLUETTI-Cloud-Dienst herzustellen.
   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. Gib deine BLUETTI-Kontodaten ein, um dich anzumelden und zu autorisieren.
   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. Bestätige, dass **Home Assistant** dein BLUETTI-Konto verknüpfen darf.
   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. Wähle anschließend die BLUETTI-Geräte aus, die du in Home Assistant verwenden
   und verwalten möchtest.
   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## ❓ Häufig gestellte Fragen (FAQ)

### **Frage:** Die BLUETTI-Integration wird nach der Installation nicht gefunden?

**Antwort:** Überprüfe, ob sich der Ordner `custom_components` am richtigen
Speicherort befindet, und starte Home Assistant neu.

### **Frage:** Die Integration bleibt offline oder kann keine Verbindung zum BLUETTI-Server herstellen?

**Antwort:** Überprüfe deine **Netzwerkverbindung**, **Port-Einstellungen** und
**Firewall**, um sicherzustellen, dass **Home Assistant** Zugriff auf die
BLUETTI-Powerstations hat.

### **Frage:** Funktioniert die BLUETTI-Integration lokal?

**Antwort:** Nein, die BLUETTI-Integration funktioniert derzeit über die Cloud.
Ein lokaler Modus befindet sich in Entwicklung, aber die Fertigstellung wird
noch etwas Zeit in Anspruch nehmen.

## 🔄 Aktualisieren der BLUETTI-Integration

### Home Assistant Operating System

1. **Aktualisiere die BLUETTI-Integration** (falls erforderlich):

   ```bash
   cd /config/custom_components/bluetti-home-assistant
   git pull
   ```

2. **Starte Home Assistant neu**, um die aktualisierte Integration zu laden:
   - Für **Home Assistant Operating System**:

     ```bash
     ha core restart
     ```

   - Für **Docker-Installationen**:

     ```bash
     docker restart container-name
     ```

### Home Assistant Community Store

Führe das Update über die HACS-Verwaltungsseite aus.

## 📮 Support & Feedback

💬 Hast du Fragen, Probleme oder Vorschläge? Teile sie uns über **GitHub
Issues** mit: [https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
