# YouTube OAuth 2.0 Einrichtung

Schritt-für-Schritt-Anleitung zur Einrichtung der YouTube-Autorisierung für das Upload-Tool.

---

## Übersicht

Das Tool verwendet **OAuth 2.0** zur Authentifizierung mit YouTube. Das bedeutet:
- **Kein API-Key** erforderlich
- Du autorisierst die App, auf dein YouTube-Konto zuzugreifen
- Einmalige Browser-Anmeldung, danach automatisch

---

## Schritt 1: Google Cloud Projekt anlegen

### 1.1 Google Cloud Console öffnen

- Gehe zu [console.cloud.google.com](https://console.cloud.google.com)
- Logge dich mit deinem Google-Konto ein

### 1.2 Neues Projekt erstellen

- Klicke oben auf **"Projekt auswählen"**
- Klicke auf **"Neues Projekt"**
- **Name:** z.B. "YouTube Upload Tool"
- **Standort:** Kann leer bleiben
- Klicke auf **"Erstellen"**
- Warte bis das Projekt erstellt ist (ca. 30 Sekunden)

---

## Schritt 2: YouTube Data API v3 aktivieren

### 2.1 API aktivieren

- Gehe zu **"APIs & Dienste"** → **"Bibliothek"**
- Suche nach: **"YouTube Data API v3"**
- Klicke auf das Suchergebnis
- Klicke auf **"Aktivieren"**

⚠️ **Wichtig:** Ohne diesen Schritt funktioniert der Upload nicht!

---

## Schritt 3: OAuth-Zustimmungsbildschirm konfigurieren

### 3.1 Zustimmungsbildschirm einrichten

- Gehe zu **"APIs & Dienste"** → **"OAuth-Zustimmungsbildschirm"**
- Wähle **"Extern"**
- Klicke **"Erstellen"**

### 3.2 App-Informationen ausfüllen

**Erforderliche Felder:**
- **App-Name:** "YouTube Upload Tool" (oder eigener Name)
- **Nutzer-Support-E-Mail:** Deine E-Mail-Adresse
- **App-Logo:** Optional, kann leer bleiben

**Entwicklerkontaktinformationen:**
- **E-Mail-Adresse:** Deine E-Mail-Adresse

Klicke **"Speichern und fortfahren"**

### 3.3 Scopes (Bereiche)

- Klicke einfach **"Speichern und fortfahren"**
- Scopes werden automatisch bei der Anmeldung angefordert

### 3.4 Testnutzer hinzufügen

⚠️ **WICHTIG:** Füge dich selbst als Testnutzer hinzu!

- Klicke auf **"+ ADD USERS"**
- Gib deine E-Mail-Adresse ein (das Konto, das Videos hochladen soll)
- Klicke **"Hinzufügen"**
- Klicke **"Speichern und fortfahren"**

### 3.5 Zusammenfassung

- Prüfe die Zusammenfassung
- Klicke **"Zurück zum Dashboard"**

---

## Schritt 4: OAuth-Client erstellen

### 4.1 Anmeldedaten erstellen

- Gehe zu **"APIs & Dienste"** → **"Anmeldedaten"**
- Klicke auf **"+ ANMELDEDATEN ERSTELLEN"**
- Wähle **"OAuth-Client-ID"**

### 4.2 Anwendungstyp wählen

- **Anwendungstyp:** Wähle **"Desktop-App"**
- **Name:** "YouTube Upload Tool Client" (oder eigener Name)
- Klicke **"Erstellen"**

### 4.3 Credentials herunterladen

- Ein Dialog erscheint: "OAuth-Client erstellt"
- Klicke auf **"JSON HERUNTERLADEN"**
- Die Datei heißt z.B. `client_secret_123456789.apps.googleusercontent.com.json`

---

## Schritt 5: Credentials platzieren

### Option A: Standard-Pfad (empfohlen)

```bash
# Erstelle Verzeichnis
mkdir -p ~/.config/yt-upload

# Verschiebe und benenne Datei um
mv ~/Downloads/client_secret_*.json ~/.config/yt-upload/client_secrets.json
```

⚠️ **Wichtig:** Die Datei MUSS `client_secrets.json` heißen!

### Option B: Repo-lokaler Pfad (automatisch erkannt)

```bash
mkdir -p .config
mv ~/Downloads/client_secret_*.json .config/client_secrets.json
```

### Option C: Eigener Pfad mit .env

Falls du einen anderen Pfad verwenden möchtest:

```bash
# Erstelle .env-Datei
cp .env.example .env

# Bearbeite .env und setze:
YOUTUBE_CLIENT_SECRETS_PATH=/pfad/zu/deiner/client_secrets.json
YOUTUBE_TOKEN_PATH=/pfad/zu/token.pickle
```

---

## Schritt 6: Erster Start und Autorisierung

### 6.1 App starten

```bash
# Aktiviere Conda-Environment
conda activate yt-upload

# Starte App
./start.sh
```

### 6.2 Upload starten

1. Wähle ein Video
2. Warte bis .info.json validiert ist
3. Wähle ein Upload-Profil
4. Klicke **"🚀 Video hochladen"**

### 6.3 Browser-Autorisierung

**Beim ersten Upload:**

1. **Browser öffnet sich automatisch**
   - Lokaler Server auf `http://localhost:8080`

2. **Google-Konto auswählen**
   - Wähle das Konto, das Videos hochladen soll
   - (Muss als Testnutzer hinzugefügt sein!)

3. **Warnung: "Google hat diese App nicht überprüft"**
   - Klicke auf **"Erweitert"**
   - Klicke auf **"Zu YouTube Upload Tool (unsicher) wechseln"**
   - Das ist normal für Apps im Testing-Modus

4. **Berechtigungen erlauben**
   - ☑️ Videos auf YouTube hochladen
   - ☑️ YouTube-Konto verwalten
   - Klicke **"Zulassen"**

5. **Erfolgsmeldung**
   - "Authentifizierung erfolgreich! Du kannst dieses Fenster schließen."
   - Schließe das Browser-Fenster

### 6.4 Token wird gespeichert

- Token wird gespeichert in: `~/.config/yt-upload/token.pickle`
- Bei zukünftigen Uploads: **Kein Browser-Login mehr nötig**
- Token wird automatisch erneuert wenn abgelaufen

---

## Problemlösung

### "OAuth2-Credentials nicht gefunden"

**Problem:** App findet `client_secrets.json` nicht

**Lösung:**
```bash
# Prüfe Pfade
ls -la ~/.config/yt-upload/client_secrets.json
ls -la .config/client_secrets.json

# Falls nicht vorhanden: Datei korrekt platzieren
mv ~/Downloads/client_secret_*.json ~/.config/yt-upload/client_secrets.json
```

---

### "Token-Refresh fehlgeschlagen"

**Problem:** Token ist beschädigt oder hat falsche Scopes

**Lösung:**
```bash
# Lösche alten Token
rm ~/.config/yt-upload/token.pickle

# Starte App neu
./start.sh

# Upload starten → Browser-Login erscheint wieder
```

---

### "Access blocked: Authorization Error"

**Problem:** Du bist nicht als Testnutzer eingetragen

**Lösung:**
1. Gehe zu [Google Cloud Console](https://console.cloud.google.com)
2. **APIs & Dienste** → **OAuth-Zustimmungsbildschirm**
3. Scrolle zu **"Testnutzer"**
4. Klicke **"+ ADD USERS"**
5. Füge deine E-Mail-Adresse hinzu
6. Versuche Upload erneut

---

### "403: Quota exceeded"

**Problem:** YouTube API Quota überschritten

**Hintergrund:**
- YouTube Data API hat tägliches Quota-Limit
- Standard: 10.000 Units/Tag
- Ein Video-Upload kostet ca. 1.600 Units

**Lösungen:**

**Kurzfristig:**
- Warte bis morgen (Quota wird um Mitternacht PST zurückgesetzt)
- Oder: Verwende ein anderes Google Cloud Projekt

**Langfristig:**
- Google Cloud Console → **APIs & Dienste** → **Kontingente**
- Suche "YouTube Data API v3"
- Klicke auf Kontingent
- Klicke **"Kontingenterhöhung anfordern"**
- Begründung angeben, z.B. "Regelmäßiger Video-Upload für Kanal"

---

### "401: Invalid credentials"

**Problem:** Client-Secret ist ungültig oder widerrufen

**Lösung:**
1. Gehe zu [Google Cloud Console](https://console.cloud.google.com)
2. **APIs & Dienste** → **Anmeldedaten**
3. Finde deinen OAuth-Client
4. Falls gelöscht: Erstelle neuen OAuth-Client
5. Lade neue `client_secrets.json` herunter
6. Platziere in `~/.config/yt-upload/`
7. Lösche Token: `rm ~/.config/yt-upload/token.pickle`
8. Starte App neu

---

### Browser öffnet sich nicht

**Problem:** Port 8080 ist bereits belegt

**Lösung:**
```bash
# Prüfe welcher Prozess Port 8080 nutzt
sudo lsof -i :8080

# Stoppe den Prozess oder wähle anderen Port
# (Erweitere app/auth.py: flow.run_local_server(port=8081))
```

---

## Sicherheitshinweise

### Token-Datei schützen

Die `token.pickle`-Datei enthält Zugriff auf dein YouTube-Konto!

**Wichtig:**
- ⚠️ Teile diese Datei NIEMALS
- ⚠️ Committe sie NICHT in Git
- ⚠️ Sichere Backups verschlüsselt

### Berechtigungen widerrufen

Falls du die Berechtigung entziehen möchtest:

1. Gehe zu [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
2. Finde "YouTube Upload Tool"
3. Klicke **"Zugriff entfernen"**

Token ist dann ungültig, neuer OAuth-Flow nötig beim nächsten Upload.

---

## Nächste Schritte

Nach erfolgreicher Einrichtung:
- Siehe **README.md** für Verwendung der App
- Siehe **docs/ARCHITECTURE.md** für technische Details
- Siehe **docs/DEVLOG.md** für Entwicklungs-Status

---

**Version:** 2.0.0
**Stand:** 2025-11-12
