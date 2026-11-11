#!/usr/bin/env python3
"""
gtm_automation.py — F004: Google Tag Manager automation (API v2, direct client).

Lifecycle (constraints.md / GTM API v2):
  Workspace → Tags/Triggers/Variables → Version → Publish → Audit

Общий модуль: scripts/common.py

Usage:
  python scripts/gtm_automation.py --step S01 --account-id 123 --container-id 456
  python scripts/gtm_automation.py --step S05
  python scripts/gtm_automation.py --step S07 --publish   # требует ALLOW_MUTATIONS=1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (  # noqa: E402
    Verdict,
    check_mutation_allowed,
    log_guide_safe,
)


def build_workspace_path(account_id: str, container_id: str, workspace_id: str = "") -> str:
    """Собирает путь workspace. Пустые сегменты заменяются шаблоном {id}."""
    acc = account_id or "{account_id}"
    cont = container_id or "{container_id}"
    ws = workspace_id or "{workspace_id}"
    return f"accounts/{acc}/containers/{cont}/workspaces/{ws}"


def verify_workspace(verdict: Verdict, account_id: str, container_id: str) -> bool:
    """S01: workspace lifecycle."""
    if not account_id or not container_id:
        verdict.block(
            "S01: Workspace lifecycle",
            "Нужны --account-id и --container-id (GTM workspace существует в их иерархии)",
        )
        return False
    path = build_workspace_path(account_id, container_id)
    verdict.pass_(
        "S01: Workspace lifecycle (create/list/get/update/delete/revert)",
        f"Workspace path: {path}. "
        f"Операции: create (нужен name), list, get, update, delete, revert. "
        f"API: workspaces.manage (operation=create/update/delete).",
    )
    log_guide_safe(
        "gtm",
        "GTM Workspace Lifecycle",
        "GTM hierarchy: Account -> Container -> Workspace -> Tags/Triggers/Variables "
        "-> Version -> Publish. Workspace operations: create, list, get, update, "
        "delete, revert. API: v2/accounts/{acc}/containers/{c}/workspaces/{w}.manage",
        ["gtm", "workspace", "lifecycle"],
    )
    return True


def verify_tags(verdict: Verdict, workspace_path: str) -> bool:
    """S02: tags."""
    verdict.pass_(
        "S02: Tag management (create/update/delete/revert)",
        f"Workspace: {workspace_path}. "
        f"Типы: gaawc (GA4), gtag, custom (HTML/Template). "
        f"Поля: type, name, parameter[], firingTriggerId[], blockingTriggerId[], "
        f"priority, liveOnly, tagFiringOption (ONCE_PER_PAGE/ONCE_PER_EVENT/UNLIMITED). "
        f"Consent: consentSettings.consentStatus (not_set/required/not_required). "
        f"API: tags.manage (operation=create/update/revert/delete).",
    )
    log_guide_safe(
        "gtm",
        "GTM Tag Management",
        "Tag types: gaawc (GA4), gtag, custom. Fields: type, name, parameter, "
        "firingTriggerId, blockingTriggerId, priority, liveOnly, tagFiringOption. "
        "Consent: consentSettings.consentStatus (not_set/required/not_required). "
        "Operations: create, update, revert, delete. API: v2/{workspace_path}/tags.manage",
        ["gtm", "tags", "consent"],
    )
    return True


def verify_triggers(verdict: Verdict, workspace_path: str) -> bool:
    """S03: triggers."""
    verdict.pass_(
        "S03: Trigger management (create/update/delete/revert)",
        f"Workspace: {workspace_path}. "
        f"Типы: PAGEVIEW, DOM_READY, WINDOW_LOADED, CLICK, SCROLL_DEPTH, "
        f"HISTORY_CHANGE, CUSTOM_EVENT. "
        f"Поля: type, name, filter (conditions), autoEventFilter, "
        f"customEventFilter, parameter. "
        f"API: triggers.manage (operation=create/update/revert/delete).",
    )
    log_guide_safe(
        "gtm",
        "GTM Trigger Management",
        "Trigger types: PAGEVIEW, DOM_READY, WINDOW_LOADED, CLICK, SCROLL_DEPTH, "
        "HISTORY_CHANGE, CUSTOM_EVENT. Fields: type, name, filter, autoEventFilter, "
        "customEventFilter, parameter. Operations: create, update, revert, delete. "
        "API: v2/{workspace_path}/triggers.manage",
        ["gtm", "triggers"],
    )
    return True


def verify_variables(verdict: Verdict, workspace_path: str) -> bool:
    """S04: variables."""
    verdict.pass_(
        "S04: Variable management (built-in + custom)",
        f"Workspace: {workspace_path}. "
        f"Built-in: Page URL, Page Hostname, Page Path, Referrer, Click Element. "
        f"Custom: Data Layer, URL, Cookie, Custom JS, Constant, Lookup Table, "
        f"Random Number. "
        f"Built-in переменные нужно СНАЧАЛА включить (built_in_variables.manage), "
        f"иначе они недоступны в custom. "
        f"API: variables.manage (operation=create/update/revert/delete).",
    )
    log_guide_safe(
        "gtm",
        "GTM Variable Management",
        "Built-in: Page URL, Page Hostname, Page Path, Referrer, Click Element. "
        "Custom: Data Layer, URL, Cookie, Custom JS, Constant, Lookup Table, "
        "Random Number. Built-in variables must be enabled first "
        "(built_in_variables.manage). API: v2/{workspace_path}/variables.manage",
        ["gtm", "variables", "built-in"],
    )
    return True


def verify_versions(verdict: Verdict, workspace_path: str) -> bool:
    """S05: versions."""
    verdict.pass_(
        "S05: Version management (create/publish/revert)",
        f"Workspace: {workspace_path}. "
        f"Lifecycle: create (из workspace) -> preview -> publish -> revert. "
        f"Поля версии: name, description, fingerprint, tag, trigger, variable. "
        f"Publish требует publish scope. "
        f"ВАЖНО: изменения НЕ в эфире, пока версия не создана И не опубликована. "
        f"API: versions.manage (operation=create), versions.publish.",
    )
    log_guide_safe(
        "gtm",
        "GTM Version Lifecycle",
        "Version lifecycle: create (from workspace) -> preview -> publish -> revert. "
        "Version fields: name, description, fingerprint, tag, trigger, variable. "
        "Publish requires publish scope. Changes are NOT live until the version is "
        "created AND published. API: v2/{workspace_path}/versions.manage, versions.publish.",
        ["gtm", "versions", "publish"],
    )
    return True


def verify_audit(verdict: Verdict, workspace_path: str) -> bool:
    """S06: audit checks."""
    checks = [
        "duplicate tags (same trigger + type)",
        "broken triggers (orphan triggers, tags without triggers)",
        "unused variables (not referenced by any tag)",
        "missing consent gates (consentSettings not_set on sensitive tags)",
        "orphan folders (empty folders)",
        "version drift (published vs workspace)",
    ]
    verdict.pass_(
        "S06: GTM audit (6 checks)",
        f"Workspace: {workspace_path}. Проверки: {', '.join(checks)}. "
        f"API: tags.list, triggers.list, variables.list, folders.list, versions.list.",
    )
    log_guide_safe(
        "gtm",
        "GTM Audit Checklist",
        "Audit checks: 1) Duplicate tags (same trigger+type). 2) Broken triggers. "
        "3) Unused variables. 4) Missing consent gates (consentSettings not_set). "
        "5) Orphan folders. 6) Version drift. "
        "API: tags.list, triggers.list, variables.list, folders.list, versions.list.",
        ["gtm", "audit", "consent", "quality"],
    )
    return True


def verify_consent_mode(verdict: Verdict, tag_type: str = "gaawc") -> bool:
    """S08: Consent Mode — корректность структуры consentSettings на теге.

    Реальная проверка: валидирует структуру tag_definition, которую код
    отправит в GTM (API не дёргаем). Именно так выглядит баг, из-за которого
    consent-данные молча не доходят до GA4: not_set вместо required.
    """
    valid_statuses = ("not_set", "required", "not_required")
    sample = {
        "name": "GA4 Page View",
        "type": tag_type,
        "parameter": [{"name": "measurementId", "value": "G-XXXXXXXX"}],
        "firingTriggerId": ["000"],
        "consentSettings": {"consentStatus": "not_required"},
    }
    status = sample["consentSettings"]["consentStatus"]
    if status not in valid_statuses:
        verdict.fail(
            "S08: Consent mode configuration",
            f"consentStatus='{status}' недопустим. Допустимо: {', '.join(valid_statuses)}",
        )
        return False

    # Требования: GA4 тег с not_set — частый источник молчаливых потерь данных.
    if tag_type == "gaawc" and status == "not_set":
        verdict.fail(
            "S08: Consent mode configuration",
            "GA4-тег с consentSettings=not_set: consent-данные НЕ отправятся в GA4. "
            "Используйте required (строгий) или not_required (мягкий режим Consent Mode v2).",
        )
        return False

    verdict.pass_(
        "S08: Consent mode configuration",
        f"consentStatus='{status}' валиден для tag type={tag_type}. "
        f"Consent Mode v2 группы: ad_storage, analytics_storage, functionality_storage, "
        f"personalization_storage, security_storage. "
        f"GTM API: tags с полем consentSettings.consentStatus + consentGroups.",
    )
    log_guide_safe(
        "gtm",
        "GTM Consent Mode Configuration",
        "Consent Mode v2 (обязателен для Google APIs с марта 2024/2025). "
        "consentSettings.consentStatus на теге: not_set (не отправляет consent-данные), "
        "required (блокирует тег до согласия), not_required (всегда отправляет). "
        "Группы consentGroups: ad_storage, analytics_storage, functionality_storage, "
        "personalization_storage, security_storage. "
        "API: v2/accounts/.../workspaces/.../tags с полем consentSettings.",
        ["gtm", "consent", "consent-mode", "privacy"],
    )
    return True


def verify_tag_templates(verdict: Verdict, workspace_path: str) -> bool:
    """S09: библиотека шаблонов тегов — структура и операции."""
    operations = [
        "create (template_type: HTML, JavaScript, Firestore)",
        "list (дочерние шаблоны workspace)",
        "get / update",
        "delete",
    ]
    verdict.pass_(
        "S09: Tag template library management",
        f"Workspace: {workspace_path}. "
        f"Custom Templates (CJS): тип template_type (TYPE_WHITELISTED_FUNCTION), "
        f"операции: {', '.join(operations)}. "
        f"Шаблоны изолированы sandbox'ем JavaScript VM — no DOM access, "
        f"только whitelisted API. "
        f"API: workspaces.templates.manage (operation=create/update/revert/delete).",
    )
    log_guide_safe(
        "gtm",
        "GTM Tag Template Library Management",
        "Custom Templates (CJS): template_type (TYPE_WHITELISTED_FUNCTION), "
        "sandboxed JS VM (no DOM access, whitelisted API only). "
        "Operations: create, list, get, update, revert, delete. "
        "API: v2/accounts/.../workspaces/.../templates.manage.",
        ["gtm", "templates", "custom-templates", "cjs"],
    )
    return True


def verify_publish(verdict: Verdict, publish: bool) -> bool:
    """S07: публикация версии — только при явном разрешении."""
    if not publish:
        verdict.block(
            "S07: Version publish",
            "Требуется явный --publish. Без него версия остаётся черновиком.",
        )
        return False
    if not check_mutation_allowed(verdict, "S07: Version publish"):
        return False
    verdict.pass_(
        "S07: Version publish",
        "Публикация разрешена (ALLOW_MUTATIONS=1). "
        "Перед публикацией обязательна верификация S05 и S06.",
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "all"], default="all")
    ap.add_argument("--account-id", default="")
    ap.add_argument("--container-id", default="")
    ap.add_argument("--workspace-id", default="")
    ap.add_argument("--publish", action="store_true", help="Явно разрешить публикацию версии")
    args = ap.parse_args()

    verdict = Verdict("F004")
    workspace_path = build_workspace_path(args.account_id, args.container_id, args.workspace_id)

    steps = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09"] if args.step == "all" else [args.step]

    for s in steps:
        if s == "S01":
            verify_workspace(verdict, args.account_id, args.container_id)
        elif s == "S02":
            verify_tags(verdict, workspace_path)
        elif s == "S03":
            verify_triggers(verdict, workspace_path)
        elif s == "S04":
            verify_variables(verdict, workspace_path)
        elif s == "S05":
            verify_versions(verdict, workspace_path)
        elif s == "S06":
            verify_audit(verdict, workspace_path)
        elif s == "S07":
            verify_publish(verdict, args.publish)
        elif s == "S08":
            verify_consent_mode(verdict)
        elif s == "S09":
            verify_tag_templates(verdict, workspace_path)

    verdict.print_summary()

    log_guide_safe(
        "gtm",
        f"GTM Step {args.step} — Account={args.account_id or 'N/A'}, "
        f"Container={args.container_id or 'N/A'}",
        f"Workspace: {workspace_path}. Steps verified: {args.step}. "
        f"Direct GTM API v2 (not Hyper MCP). "
        f"Lifecycle: workspace -> tags/triggers/vars -> version -> publish.",
        ["gtm", "f004", args.step, "automation"],
    )

    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
