# Cloudflare Pages Deploy Automation — F012

> Cloudflare Pages deploy → GSC sitemap + URL indexing. Target: 13 pages priority.
> Code: `scripts/cloudflare_pages_gsc.py` + `scripts/cloudflare_deploy_hook.py`

## Commands (тестируются сейчас)

```
# Валидация структуры (всегда, без credentials)
python scripts/cloudflare_pages_gsc.py --step S01 --deployed-url https://test.pages.dev

# Мутации (самостоятельно или через deploy)
python scripts/cloudflare_pages_gsc.py --step S02 --deployed-url https://test.pages.dev
```

## Deploy hook (на сайте)

```bash
# После Cloudflare Build завершился — вызовиte чтобы запустить:
python scripts/cloudflare_deploy_hook.py --action verify_deploy --project-id my-site --deployed-url https://test.pages.dev
```

## Безопасность

- `ALLOW_MUTATIONS=0` — все мутации BLOCKED по умолчанию
- Sitemaps и indexing — dry-run по умолчанию
- `ADS_MAX_MUTATION_MICROS` — не для Cloudflare (GSS использует GSS pages budget)
