# Google SEO Automation

Automatisation de Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads et des réponses IA (AI Overviews / AEO) sur une **base de
connaissances interne auto-mise à jour** des API Google, construite à partir
de documents de découverte officiels et lisibles par machine.

> État : l'infrastructure de la base de connaissances est opérationnelle. Les
> intégrations GA4/GTM/GSC/Ads sont implémentées et vérifiées ; les appels API
> en direct nécessitent des identifiants (voir `.env.example`).

---

## Ce qui fonctionne

- **312 endpoints** extraits de 7 documents de découverte Google, automatiquement
- **Recherche en texte intégral** dans le wiki (SQLite FTS5, sans dépendances externes)
- **Détection de changements** via SHA256 + journal d'audit `change_log`
- **Vérification de fraîcheur** avec seuil de 14 jours et planification cron
- **16 tests de régression** couvrant 4 bugs trouvés pendant le développement
- **7 rôles d'agent** avec des contrats d'entrée/sortie explicites
- **8 sur 11 features** vérifiées (PASS) ; 3 bloquées uniquement par des identifiants externes

## Démarrage rapide

```bash
cd project

# 1. Vérifier l'environnement et installer les dépendances
./init.sh

# 2. Créer / mettre à jour le schéma de BD (idempotent, avec migrations)
python scripts/init_db.py

# 3. Récupérer la documentation fraîche de Google
python scripts/sync_wiki.py --full

# 4. Vérifier que tout est à jour
python scripts/sync_wiki.py --check-freshness
```

## Sources d'API (mesuré le 2026-10-12)

| Source | Document de découverte | Endpoints |
|--------|----------------------|-----------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (aucune méthode) |
| **Total** | | **312** |

## Structure

Voir [README.md](README.md) (anglais) pour la structure complète du projet.

## Sécurité

- `.env` est dans `.gitignore` ; le modèle est `.env.example`
- Les secrets proviennent uniquement des variables d'environnement
- Les mutations sont dry-run par défaut (`ALLOW_MUTATIONS=0`)
- La base de données est un cache — elle est régénérée à partir des sources

## Documentation

- [Architecture](project/docs/architecture.md)
- [Journal des modifications](project/docs/progress.md)
- [Référence API](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

[MIT](LICENSE)