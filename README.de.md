# Google SEO Automation

Automatisierung von Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads und KI-Antworten (AI Overviews / AEO) über eine **selbstaktualisierende
interne Wissensbasis** von Google-APIs, aufgebaut aus offiziellen
maschinenlesbaren Discovery-Dokumenten.

> Status: Die Wissensbasis-Infrastruktur ist betriebsbereit. GA4/GTM/GSC/Ads-
> Integrationen sind implementiert und verifiziert; Live-API-Aufrufe erfordern
> Credentials (siehe `.env.example`).

---

## Was funktioniert

- **312 Endpunkte** aus 7 Google Discovery-Dokumenten, automatisch extrahiert
- **Volltextsuche** in der Wiki (SQLite FTS5, keine externen Abhängigkeiten)
- **Änderungserkennung** via SHA256 + `change_log`-Audit-Trail
- **Aktualitätsprüfung** mit 14-Tage-Schwelle und Cron-Zeitplan
- **16 Regressionstests** für 4 während der Entwicklung gefundene Bugs
- **7 Rollenrollen** mit expliziten Ein-/Ausgabe-Verträgen
- **8 von 11 Features** verifiziert (PASS); 3 blockiert nur durch externe Credentials

## Schnellstart

```bash
cd project

# 1. Umgebung prüfen und Abhängigkeiten installieren
./init.sh

# 2. Datenbankschema erstellen / aktualisieren (idempotent, mit Migrationen)
python scripts/init_db.py

# 3. Frische Dokumentation von Google holen
python scripts/sync_wiki.py --full

# 4. Prüfen, ob alles aktuell ist
python scripts/sync_wiki.py --check-freshness
```

## API-Quellen (gemessen 2026-10-12)

| Quelle | Discovery-Dokument | Endpunkte |
|--------|-------------------|-----------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (keine Methoden) |
| **Gesamt** | | **312** |

## Struktur

Siehe [README.md](README.md) (Englisch) für die vollständige Projektstruktur.

## Sicherheit

- `.env` ist in `.gitignore`; Vorlage ist `.env.example`
- Secrets kommen nur aus Umgebungsvariablen
- Mutationen sind standardmäßig dry-run (`ALLOW_MUTATIONS=0`)
- Die Datenbank ist ein Cache — wird aus den Quellen regeneriert

## Dokumentation

- [Architektur](project/docs/architecture.md)
- [Änderungsprotokoll](project/docs/progress.md)
- [API-Referenz](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## Mitwirken

Siehe [CONTRIBUTING.md](CONTRIBUTING.md).

## Lizenz

[MIT](LICENSE)