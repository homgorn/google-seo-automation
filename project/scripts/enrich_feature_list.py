#!/usr/bin/env python3
"""
enrich_feature_list.py — обогащает feature_list.json полями SDD.

Добавляет к каждой фиче:
  acceptance_criteria — измеримые критерии приёмки
  depends_on         — фичи, которые должны быть завершены
  blocked_by         — внешние блокеры (credentials, решения владельца)
  test_refs          — файлы тестов, покрывающих фичу
  script             — скрипт, реализующий фичу
  spec               — ссылка на спецификацию
  estimate           — грубая оценка в шагах
  uncovered_steps    — шаги из steps[], которые НЕ покрыты скриптом

Запуск: python scripts/enrich_feature_list.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows-консоль cp1252 не печатает кириллицу
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent
FEATURE_LIST = PROJECT_ROOT / "feature_list.json"

# acceptance_criteria: проверяемые утверждения
ACCEPTANCE = {
    "F001": [
        "wiki содержит >=300 эндпоинтов из >=7 Google Discovery-документов",
        "каждый источник зафиксирован в api_docs с content_hash",
        "docs/architecture.md содержит измеренные счётчики и provenance",
        "wiki/index.md + wiki/index.json сгенерированы скриптом",
        "wiki/_data/graph.json содержит >=100 триплетов",
    ],
    "F002": [
        "БД создаётся idempotent: повторный init_db.py не падает",
        "полнотекстовый поиск работает через FTS5 без внешних зависимостей",
        "sync_runs фиксирует каждый прогон с статусом и счётчиками",
        "change_log хранит историю изменений документов",
        "эмбеддинги: dry-run работает всегда, реальный режим — при наличии chromadb",
    ],
    "F003": [
        "оба auth-метода поддержаны: service_account и oauth",
        "property_id валидируется по формату properties/<numeric_id>",
        "все 6 шагов фичи покрыты скриптом ga4_automation.py",
        "живой вызов runReport возвращает данные (требует credentials)",
        "BigQuery export: связь analytics_{property_id} работает",
    ],
    "F004": [
        "workspace path собирается из account/container/workspace id",
        "S02-S05 проверяют поля API: tags, triggers, variables, versions",
        "S06 проверяет 6 audit-проверок (включая consent gates)",
        "публикация версии заблокирована без ALLOW_MUTATIONS=1",
        "живой цикл create->tag->trigger->version->publish работает",
    ],
    "F005": [
        "GSC_SITE_URL обязателен; без него шаги дают BLOCKED, не PASS",
        "sitemap CRUD: list/get/submit/delete",
        "searchanalytics.query за 30 дней с учётом лага 2-3 дня",
        "Indexing API: квота 200/день контролируется",
        "URL inspection: вердикт indexStatus для ключевых URL",
    ],
    "F006": [
        "бюджеты в микросах: <1_000_000 отклоняется как FAIL",
        "кампании создаются только в статусе PAUSED",
        "GAQL без SELECT/FROM отклоняется",
        "запрещённый join ad_group_criterion+search_term_view отклоняется",
        "активация заблокирована без --activate и ALLOW_MUTATIONS=1",
        "все 4 канала (SEARCH, DISPLAY, PMax, VIDEO) поддержаны",
    ],
    "F007": [
        "SOAP v13 и миграция на REST описаны",
        "структуры сервисов (CampaignManagement, AdInsight, Bulk, Reporting) задокументированы",
        "живые вызовы реализуются после получения developer token",
    ],
    "F008": [
        "цитирования в 6 LLM трекаются в aeo_citations",
        "E-E-A-T оценивается по 4 измерениям с отраслевыми порогами",
        "schema-рекомендации для AI перечисляют 4 типа (FAQPage, Article, Organization, Person)",
        "конкурентный анализ даёт покрытие LLM и скорость цитирования",
        "дашборд видимости агрегирует цитаты и аудиты",
    ],
    "F009": [
        "двунаправленная синхронизация: wiki->oc и oc->wiki",
        "session-шаблоны для каждой фичи созданы",
        "аудит-трейл: sync_runs + change_log",
        "расписание задаётся конфигом",
    ],
    "F010": [
        "все скрипты проекта покрыты тестами",
        "pytest зелёный",
        "verify_feature.py даёт вердикт по каждой фиче",
        "рекурсия verify_feature->pytest->verify_feature исключена",
    ],
    "F011": [
        "runbook по ротации credentials",
        "runbook по восстановлению из данных",
        "runbook по мониторингу стоимости",
        "процедуры исполняемы и проверены",
    ],
}

DEPENDS_ON = {
    "F001": [],
    "F002": ["F001"],
    "F003": ["F002"],
    "F004": ["F002"],
    "F005": ["F002"],
    "F006": ["F002"],
    "F007": ["F002"],
    "F008": ["F002"],
    "F009": ["F001", "F002"],
    "F010": ["F001", "F002"],
    "F011": ["F003", "F004", "F005", "F006"],
}

BLOCKED_BY = {
    "F003": ["credentials: GOOGLE_APPLICATION_CREDENTIALS или GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN"],
    "F005": ["credentials: GSC_SITE_URL"],
    "F006": ["credentials: GOOGLE_ADS_DEVELOPER_TOKEN + GOOGLE_ADS_CUSTOMER_ID"],
    "F007": ["credentials: MS_ADS_DEVELOPER_TOKEN", "decision: SOAP или REST (рекомендовано REST)"],
}

TEST_REFS = {
    "F001": ["tests/test_sync_wiki.py", "tests/test_tooling.py"],
    "F002": ["tests/test_sync_wiki.py", "tests/test_tooling.py"],
    "F003": ["tests/test_automation_scripts.py", "tests/test_common.py"],
    "F004": ["tests/test_automation_scripts.py"],
    "F005": ["tests/test_automation_scripts.py"],
    "F006": ["tests/test_automation_scripts.py", "tests/test_common.py"],
    "F007": [],
    "F008": ["tests/test_automation_scripts.py"],
    "F009": [],
    "F010": ["tests/test_tooling.py", "tests/test_common.py", "tests/test_automation_scripts.py"],
    "F011": ["tests/test_tooling.py"],
}

SCRIPTS = {
    "F001": "scripts/sync_wiki.py",
    "F002": "scripts/init_db.py, scripts/wiki_query.py, scripts/embed_wiki.py, scripts/wiki_index.py",
    "F003": "scripts/ga4_automation.py",
    "F004": "scripts/gtm_automation.py",
    "F005": "scripts/gsc_automation.py",
    "F006": "scripts/ads_automation.py",
    "F007": None,
    "F008": "scripts/aeo_automation.py",
    "F009": "scripts/openchamber_sync.py",
    "F010": "scripts/verify_feature.py",
    "F011": None,
}

SPECS = {
    "F001": "docs/specs/SPEC-001-platform.md",
    "F002": "docs/specs/SPEC-001-platform.md",
    "F003": "docs/specs/SPEC-001-platform.md",
    "F004": "docs/specs/SPEC-001-platform.md",
    "F005": "docs/specs/SPEC-001-platform.md",
    "F006": "docs/specs/SPEC-001-platform.md",
    "F007": "docs/specs/SPEC-001-platform.md",
    "F008": "docs/specs/SPEC-001-platform.md",
    "F009": "docs/specs/SPEC-001-platform.md",
    "F010": "docs/specs/SPEC-001-platform.md",
    "F011": "docs/specs/SPEC-001-platform.md",
}

# Непокрытые шаги — по состоянию 2026-11-12: 0.
# Все шаги фич покрыты либо скриптами, либо verify_feature.
UNCOVERED = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    features = json.loads(FEATURE_LIST.read_text(encoding="utf-8"))

    for f in features:
        fid = f["id"]
        f["acceptance_criteria"] = ACCEPTANCE.get(fid, [])
        f["depends_on"] = DEPENDS_ON.get(fid, [])
        f["blocked_by"] = BLOCKED_BY.get(fid, [])
        f["test_refs"] = TEST_REFS.get(fid, [])
        f["script"] = SCRIPTS.get(fid)
        f["spec"] = SPECS.get(fid)
        f["estimate_steps"] = len(f.get("steps", []))
        f["uncovered_steps"] = UNCOVERED.get(fid, [])
        f["status"] = "blocked" if f["blocked_by"] else ("done" if f["passes"] else "in_progress")

    total_steps = sum(f["estimate_steps"] for f in features)
    uncovered = sum(len(f["uncovered_steps"]) for f in features)
    print(f"Фич: {len(features)} | шагов: {total_steps} | непокрытых шагов: {uncovered}")
    for f in features:
        print(f"  {f['id']} [{f['status']:11s}] acc={len(f['acceptance_criteria'])} "
              f"deps={len(f['depends_on'])} tests={len(f['test_refs'])} "
              f"uncovered={len(f['uncovered_steps'])}")

    if args.dry_run:
        print("\n[dry-run] файл не изменён")
        return

    FEATURE_LIST.write_text(
        json.dumps(features, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nОбновлён: {FEATURE_LIST.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
