# Google SEO Automation

Automatización de Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads y respuestas de IA (AI Overviews / AEO) sobre una **base de
conocimiento interna autoactualizable** de las APIs de Google, construida a partir
de documentos de descubrimiento oficiales y legibles por máquina.

> Estado: la infraestructura de la base de conocimiento está operativa. Las
> integraciones de GA4/GTM/GSC/Ads están implementadas y verificadas; las
> llamadas a la API en vivo requieren credenciales (ver `.env.example`).

---

## Qué funciona

- **312 endpoints** extraídos de 7 documentos de descubrimiento de Google
- **Búsqueda de texto completo** en la wiki (SQLite FTS5, sin dependencias externas)
- **Detección de cambios** mediante SHA256 + registro de auditoría `change_log`
- **Verificación de frescura** con umbral de 14 días y programación cron
- **16 tests de regresión** que cubren 4 bugs encontrados durante el desarrollo
- **7 roles de agente** con contratos de entrada/salida explícitos
- **8 de 11 features** verificadas (PASS); 3 bloqueadas solo por credenciales externas

## Inicio rápido

```bash
cd project

# 1. Comprobar entorno e instalar dependencias
./init.sh

# 2. Crear / actualizar esquema de BD (idempotente, con migraciones)
python scripts/init_db.py

# 3. Obtener documentación fresca de Google
python scripts/sync_wiki.py --full

# 4. Verificar que todo esté actualizado
python scripts/sync_wiki.py --check-freshness
```

## Fuentes de API (medido 2026-10-12)

| Fuente | Documento de descubrimiento | Endpoints |
|--------|----------------------------|-----------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (sin métodos) |
| **Total** | | **312** |

## Estructura del proyecto

Ver [README.md](README.md) (inglés) para la estructura completa del proyecto.

## Seguridad

- `.env` está en `.gitignore`; la plantilla es `.env.example`
- Los secretos vienen solo de variables de entorno
- Las mutaciones son dry-run por defecto (`ALLOW_MUTATIONS=0`)
- La base de datos es un caché — se regenera desde las fuentes

## Documentación

- [Arquitectura](project/docs/architecture.md)
- [Registro de cambios](project/docs/progress.md)
- [Referencia de API](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

[MIT](LICENSE)