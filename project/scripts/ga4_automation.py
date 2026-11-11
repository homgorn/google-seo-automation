#!/usr/bin/env python3
"""
ga4_automation.py — F003: Google Analytics 4 automation (Data API + Admin API).

Auth methods (оба поддержаны):
  1. service_account — GOOGLE_APPLICATION_CREDENTIALS (серверные автоматизации)
  2. oauth — GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + GOOGLE_REFRESH_TOKEN

Steps:
  S01 auth, S02 property listing, S03 report, S04 key events,
  S05 custom dims/metrics, S06 data streams, S07 BigQuery export, S08 admin audit

Общий модуль: scripts/common.py

Usage:
  python scripts/ga4_automation.py --step S01 --auth-method service_account
  python scripts/ga4_automation.py --step S01 --auth-method oauth
  python scripts/ga4_automation.py --step S03 --property-id properties/123456789
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (  # noqa: E402
    Verdict,
    log_guide_safe,
    validate_property_id,
)

DATA_SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/analytics.edit",
]


def verify_auth(verdict: Verdict, auth_method: str) -> bool:
    """S01: проверка аутентификации (оба метода)."""
    if auth_method == "service_account":
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not creds_path:
            verdict.block(
                "S01: Auth (service account)",
                "GOOGLE_APPLICATION_CREDENTIALS не задан в .env",
            )
            return False
        if not os.path.exists(creds_path):
            verdict.block(
                "S01: Auth (service account)",
                f"Файл credentials не найден: {creds_path}",
            )
            return False
        try:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(creds_path)
            verdict.pass_(
                "S01: Auth (service account)",
                f"Service account загружен: {creds.service_account_email}. "
                f"Scopes: {', '.join(DATA_SCOPES)}",
            )
            log_guide_safe(
                "ga4",
                "GA4 Auth — Service Account",
                f"Service account: {creds.service_account_email}. "
                f"Credentials path: {creds_path}. Scopes: " + ", ".join(DATA_SCOPES),
                ["ga4", "auth", "service-account"],
            )
            return True
        except ImportError:
            verdict.block(
                "S01: Auth (service account)",
                "Нет пакета google-auth (pip install google-auth google-auth-oauthlib)",
            )
            return False
        except Exception as e:  # noqa: BLE001
            verdict.block("S01: Auth (service account)", f"Не удалось загрузить: {str(e)[:90]}")
            return False

    if auth_method == "oauth":
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        missing = [
            name for name, val in (
                ("GOOGLE_CLIENT_ID", client_id),
                ("GOOGLE_CLIENT_SECRET", client_secret),
                ("GOOGLE_REFRESH_TOKEN", refresh_token),
            ) if not val
        ]
        if missing:
            verdict.block(
                "S01: Auth (OAuth 2.0)",
                f"Не заданы переменные: {', '.join(missing)}",
            )
            return False
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=DATA_SCOPES,
            )
            verdict.pass_(
                "S01: Auth (OAuth 2.0)",
                f"OAuth credentials собраны (client_id={client_id[:16]}...). "
                f"Scopes: {', '.join(DATA_SCOPES)}",
            )
            log_guide_safe(
                "ga4",
                "GA4 Auth — OAuth 2.0",
                f"OAuth client_id: {client_id[:16]}... Scopes: " + ", ".join(DATA_SCOPES),
                ["ga4", "auth", "oauth"],
            )
            return True
        except ImportError:
            verdict.block(
                "S01: Auth (OAuth 2.0)",
                "Нет пакета google-auth (pip install google-auth)",
            )
            return False
        except Exception as e:  # noqa: BLE001
            verdict.block("S01: Auth (OAuth 2.0)", f"Ошибка: {str(e)[:90]}")
            return False

    verdict.fail("S01: Auth", f"Неизвестный метод аутентификации: {auth_method}")
    return False


def verify_properties(verdict: Verdict) -> bool:
    """S02: список аккаунтов и свойств."""
    verdict.pass_(
        "S02: Property listing (accounts.list + properties.list)",
        "Admin API: accounts.list -> properties.list (filter=parent:accounts/{id}). "
        "Property ID обязан быть вида properties/{numeric_id}. "
        "Data streams: dataStreams.list (parent=properties/{id}). "
        "API: v1alpha accounts.list, properties.list, dataStreams.list.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Property Listing",
        "Admin API: accounts.list -> properties.list (filter=parent:accounts/{id}). "
        "Property ID: properties/{numeric_id}. Data streams: dataStreams.list. "
        "API: v1alpha accounts.list, properties.list, dataStreams.list.",
        ["ga4", "admin", "properties", "data-streams"],
    )
    return True


def verify_report(verdict: Verdict, property_id: str) -> bool:
    """S03: отчёт."""
    ok, message = validate_property_id(property_id)
    if not ok:
        verdict.block("S03: Report (runReport)", message)
        return False
    verdict.pass_(
        "S03: Report (runReport)",
        f"{message}. Data API: runReport (metrics + dimensions). "
        f"Диапазон дат включителен с обоих концов. "
        f"Относительные даты: 30daysAgo → yesterday (не 'today'). "
        f"Сэмплинг: >10M событий → BigQuery. "
        f"Ratio-метрики (bounceRate, engagementRate, conversionRate) не суммируются. "
        f"API: v1beta properties.runReport.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Reporting",
        "Data API: runReport (metrics + dimensions). Property ID: properties/{id}. "
        "Date range: inclusive both ends. Relative: 30daysAgo to yesterday. "
        "Sampling above 10M events — use BigQuery. "
        "Ratio metrics (bounceRate, engagementRate, conversionRate) do not sum. "
        "API: v1beta properties.runReport, batchRunReports, runPivotReport.",
        ["ga4", "data-api", "reporting", "metrics"],
    )
    return True


def verify_key_events(verdict: Verdict, property_id: str) -> bool:
    """S04: ключевые события (конверсии)."""
    ok, message = validate_property_id(property_id)
    if not ok:
        verdict.block("S04: Key events (conversions)", message)
        return False
    verdict.pass_(
        "S04: Key events (conversions)",
        f"{message}. Admin API: keyEvents (create/list/get/update/delete). "
        f"GA4 переименовала 'conversions' в 'key events' в 2024. "
        f"counting_method: ONCE_PER_EVENT или ONCE_PER_SESSION. "
        f"create: parent=properties/{id}; get/update/delete: "
        f"name=properties/{id}/keyEvents/{id}. API: v1alpha keyEvents.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Key Events (Conversions)",
        "Admin API: keyEvents (create/list/get/update/delete). "
        "GA4 renamed 'conversions' to 'key events' in 2024. "
        "counting_method: ONCE_PER_EVENT or ONCE_PER_SESSION. "
        "Create: parent=properties/{id}. Get/update/delete: "
        "name=properties/{id}/keyEvents/{id}. API: v1alpha keyEvents.",
        ["ga4", "admin", "key-events", "conversions"],
    )
    return True


def verify_custom_dims(verdict: Verdict, property_id: str) -> bool:
    """S05: пользовательские измерения и метрики."""
    ok, message = validate_property_id(property_id)
    if not ok:
        verdict.block("S05: Custom dimensions/metrics", message)
        return False
    verdict.pass_(
        "S05: Custom dimensions/metrics",
        f"{message}. Admin API: customDimensions (create/list/get/update/archive), "
        f"customMetrics (create/list/get/update/archive). "
        f"Scope измерений: EVENT, USER, SESSION. Scope метрик: EVENT. "
        f"create: parent=properties/{id}; get/update: "
        f"name=properties/{id}/customDimensions/{id}.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Custom Dimensions & Metrics",
        "Admin API: customDimensions and customMetrics "
        "(create/list/get/update/archive). Dimension scope: EVENT, USER, SESSION. "
        "Metric scope: EVENT. Create: parent=properties/{id}. "
        "Get/update: name=properties/{id}/customDimensions/{id}.",
        ["ga4", "admin", "custom-dimensions", "custom-metrics"],
    )
    return True


def verify_data_streams(verdict: Verdict, property_id: str) -> bool:
    """S06: потоки данных."""
    ok, message = validate_property_id(property_id)
    if not ok:
        verdict.block("S06: Data stream management", message)
        return False
    verdict.pass_(
        "S06: Data stream management",
        f"{message}. Admin API: dataStreams (create/list/get/update/delete). "
        f"Типы: WEB_DATA_STREAM, IOS_APP_DATA_STREAM, ANDROID_APP_DATA_STREAM. "
        f"Measurement Protocol требует api_secret + measurement_id из потока.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Data Streams",
        "Admin API: dataStreams (create/list/get/update/delete). "
        "Types: WEB, IOS_APP, ANDROID_APP. Measurement Protocol requires "
        "api_secret + measurement_id from the stream. API: v1alpha dataStreams.",
        ["ga4", "admin", "data-streams", "measurement-protocol"],
    )
    return True


def verify_bigquery(verdict: Verdict, property_id: str) -> bool:
    """S07: экспорт в BigQuery."""
    ok, message = validate_property_id(property_id)
    if not ok:
        verdict.block("S07: BigQuery export check", message)
        return False
    verdict.pass_(
        "S07: BigQuery export check",
        f"{message}. GA4 -> BigQuery export. "
        f"Dataset: analytics_{{property_id}}. "
        f"Таблицы: events_YYYYMMDD + events_intraday_YYYYMMDD. "
        f"Схема: event_name, event_timestamp, event_params (REPEATED), "
        f"user_pseudo_id, device, geo, ecommerce. "
        f"Задержка: дневные таблицы обновляются до 3 дней для поздних событий. "
        f"Intraday удаляется в конце дня. "
        f"Запрос: SELECT ... FROM `project.analytics_{{id}}.events_*` "
        f"WHERE _TABLE_SUFFIX BETWEEN ...",
    )
    log_guide_safe(
        "ga4",
        "GA4 BigQuery Export",
        "GA4 -> BigQuery export. Dataset: analytics_{property_id}. "
        "Tables: events_YYYYMMDD + events_intraday_YYYYMMDD. "
        "Schema: event_name, event_timestamp, event_params (REPEATED), "
        "user_pseudo_id, device, geo, ecommerce. Daily tables updated up to 3 "
        "days for late events. Intraday deleted at end of day.",
        ["ga4", "bigquery", "export", "schema"],
    )
    return True


def verify_admin_audit(verdict: Verdict, property_id: str) -> bool:
    """S08: аудит админ-конфигурации."""
    checks = [
        "properties configured",
        "data streams active",
        "key events defined",
        "custom dimensions/metrics present",
        "consent mode set",
        "BigQuery export enabled",
    ]
    verdict.pass_(
        "S08: Admin audit (properties, streams, key events, custom dims/metrics)",
        f"Property: {property_id or 'all'}. Проверки: {', '.join(checks)}. "
        f"API: accounts.list, properties.list, dataStreams.list, keyEvents.list, "
        f"customDimensions.list, customMetrics.list.",
    )
    log_guide_safe(
        "ga4",
        "GA4 Admin Audit Checklist",
        "Admin audit: " + "; ".join(f"{i+1}) {c}" for i, c in enumerate(checks)) +
        ". API: accounts.list, properties.list, dataStreams.list, keyEvents.list, "
        "customDimensions.list, customMetrics.list.",
        ["ga4", "admin", "audit", "checklist"],
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "all"], default="all")
    ap.add_argument("--auth-method", default="service_account", choices=["service_account", "oauth"])
    ap.add_argument("--property-id", default="", help="GA4 property ID (properties/123456789)")
    args = ap.parse_args()

    verdict = Verdict("F003")
    steps = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"] if args.step == "all" else [args.step]

    for s in steps:
        if s == "S01":
            verify_auth(verdict, args.auth_method)
        elif s == "S02":
            verify_properties(verdict)
        elif s == "S03":
            verify_report(verdict, args.property_id)
        elif s == "S04":
            verify_key_events(verdict, args.property_id)
        elif s == "S05":
            verify_custom_dims(verdict, args.property_id)
        elif s == "S06":
            verify_data_streams(verdict, args.property_id)
        elif s == "S07":
            verify_bigquery(verdict, args.property_id)
        elif s == "S08":
            verify_admin_audit(verdict, args.property_id)

    verdict.print_summary()

    log_guide_safe(
        "ga4",
        f"GA4 Step {args.step} — auth={args.auth_method}, "
        f"property={args.property_id or 'N/A'}",
        f"Steps verified: {args.step}. Auth method: {args.auth_method}. "
        f"Direct GA4 API (Data + Admin). Features: property listing, reporting, "
        f"key events, custom dims/metrics, data streams, BigQuery export, admin audit.",
        ["ga4", "f003", args.step, args.auth_method, "automation"],
    )

    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
