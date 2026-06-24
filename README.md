# Midea PortaSplit Verfügbarkeits-Checker

Durchsucht automatisch Baumärkte und Online-Shops nach der **Midea PortaSplit**.
Sobald ein Treffer verfügbar wird, verschickt GitHub Actions eine E-Mail an dich.

## Wie es funktioniert

1. `checker.py` lädt die in `config.json` hinterlegten Shop-/Produktseiten.
2. Pro Seite wird der Text auf Schlüsselwörter geprüft
   (`available_keywords` z.B. „In den Warenkorb", `unavailable_keywords` z.B. „nicht verfügbar").
3. Wird etwas **neu** verfügbar (Wechsel von nicht-verfügbar → verfügbar),
   schickt der Workflow eine E-Mail. `state.json` merkt sich den letzten Zustand,
   damit du nicht bei jedem Lauf erneut gemailt wirst.
4. Der Workflow läuft per Zeitplan (alle 30 Min.) und lässt sich auch manuell starten.

## Einrichtung (einmalig)

### 1. Repository auf GitHub anlegen
```bash
cd C:\Users\admin.DUEBEL\Documents\braucheklima
git init
git add .
git commit -m "Initial: Midea PortaSplit Checker"
git branch -M main
git remote add origin https://github.com/<DEIN-USER>/<REPO>.git
git push -u origin main
```

### 2. Gmail App-Passwort erstellen
Normale Gmail-Passwörter funktionieren nicht für SMTP. Du brauchst ein **App-Passwort**:
1. Google-Konto → Sicherheit → **Bestätigung in zwei Schritten** aktivieren (Pflicht).
2. Dann unter https://myaccount.google.com/apppasswords ein App-Passwort
   („Mail" / Gerät beliebig) erzeugen → 16-stelligen Code kopieren.

### 3. GitHub Secrets hinterlegen
Im Repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name            | Wert                                      |
|-----------------|-------------------------------------------|
| `MAIL_USERNAME` |          |
| `MAIL_PASSWORD` | das 16-stellige App-Passwort (ohne Leerzeichen) |
| `MAIL_TO`       |           |

### 4. Actions aktivieren
Tab **Actions** im Repo öffnen und Workflows aktivieren, falls gefragt.
Du kannst den Lauf sofort manuell über **„Run workflow"** testen.

## URLs / Produkte anpassen

Alles steckt in `config.json`. Trage unter `targets` die konkreten
**Produktseiten** ein, die du beobachten willst. Beispiel:

```json
{
  "name": "OBI - Midea PortaSplit 3,5 kW",
  "shop": "OBI",
  "url": "https://www.obi.de/.../p/123456",
  "available_keywords": ["in den warenkorb"],
  "unavailable_keywords": ["nicht verfügbar"]
}
```
Lässt du `available_keywords`/`unavailable_keywords` weg, gelten die globalen
Werte aus `defaults`.

## Wichtige Hinweise / Grenzen

- Manche Shops (v.a. **Amazon**, teilweise **OBI**) setzen Bot-Schutz ein oder
  laden Inhalte per JavaScript nach. Dann liefert die Seite evtl. keinen
  brauchbaren Text → Status „❓ unklar". In dem Fall am besten die **direkte
  Produktseiten-URL** statt der Suchseite eintragen und die Keywords anpassen.
- Prüfe nach dem ersten echten Lauf im Actions-Log, was erkannt wurde, und
  feile an den Keywords / URLs.
- Der Zeitplan (`*/30`) lässt sich in `.github/workflows/check.yml` ändern.
- GitHub-Cron startet bei Last gelegentlich verspätet — das ist normal.

## Lokal testen

```bash
pip install -r requirements.txt
python checker.py
```
Das schreibt Ergebnisse in die Konsole und aktualisiert `state.json`.
