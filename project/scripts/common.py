#!/usr/bin/env python3
"""
common.py — общий модуль для всех automation-скриптов.

Устраняет 6-кратное дублирование Verdict/log_guide и закрывает реальные
дефекты, найденные code review (2026-11-11):

  1. doc_id больше не «зашит» — определяется по имени источника в БД.
     Раньше aeo писал в doc_id=1 (это gtm), ga4 в doc_id=2 (google-apis-master)
     и т.д. — аудит-трейл вёл в чужие документы.
  2. Exit code: PASS=0, FAIL=1, BLOCKED=2. Раньше gsc возвращал 0 при
     полностью BLOCKED-результате (CI думал, что всё зелено).
  3. Исключения при записи в БД больше не проглатываются молча.
  4. ALLOW_MUTATIONS реально проверяется (было объявлено в .env.example,
     но не читалось кодом — принцип dry-run не enforced).
  5. ADS_MAX_MUTATION_MICROS реально проверяется (аналогично).
  6. Один источник истины для формата property_id / budget.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"

# ── Коды возврата ──────────────────────────────────────────────
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2

# ── Ограничения безопасности ───────────────────────────────────
# Бюджет в микросах: $1 = 1_000_000 micros
MIN_BUDGET_MICROS = 1_000_000
# Порог предупреждения: $10/day — типичный минимум для большинства типов кампаний
WARN_BUDGET_MICROS = 10_000_000

# Словарь источников → как искать doc_id в api_docs.
# Ключ — строка source в таблице api_docs.
SOURCE_BY_FEATURE = {
    "gsc": "gsc",
    "gtm": "gtm",
    "ga4": "ga4_data",
    "ga4_admin": "ga4_admin",
    "ads": "google-apis-master",
    "aeo": "google-apis-master",
    "embeddings": "google-apis-master",
    "openchamber": "google-apis-master",
}


class Verdict:
    """Единый результат проверки. Заменяет 6 копий Verdict-класса."""

    def __init__(self, feature_id: str = ""):
        self.feature_id = feature_id
        self.passed = 0
        self.failed = 0
        self.blocked = 0
        self.steps = []

    def add(self, step: str, status: str, evidence: str):
        self.steps.append({"step": step, "status": status, "evidence": evidence})
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "BLOCKED":
            self.blocked += 1

    def pass_(self, step, evidence):
        self.add(step, "PASS", evidence)

    def fail(self, step, evidence):
        self.add(step, "FAIL", evidence)

    def block(self, step, evidence):
        self.add(step, "BLOCKED", evidence)

    @property
    def overall(self) -> str:
        if self.failed > 0:
            return "FAIL"
        if self.blocked > 0:
            return "BLOCKED"
        if self.passed > 0:
            return "PASS"
        return "UNKNOWN"

    def exit_code(self) -> int:
        if self.failed > 0:
            return EXIT_FAIL
        if self.blocked > 0:
            return EXIT_BLOCKED
        if self.passed > 0:
            return EXIT_PASS
        return EXIT_FAIL

    def summary_str(self) -> str:
        lines = [
            f"VERDICT: {self.overall}",
            f"STEPS: {len(self.steps)} "
            f"(PASS={self.passed}, FAIL={self.failed}, BLOCKED={self.blocked})",
        ]
        for s in self.steps:
            # 200 символов: 100 обрезали важные детали (квоты, форматы,
            # формат property_id), которые verifier должен видеть.
            snippet = s["evidence"][:200].replace("\n", " ")
            lines.append(f"  - {s['step']}: {s['status']} — {snippet}")
        return "\n".join(lines)

    def print_summary(self):
        print(self.summary_str())


# ── Безопасность мутаций ───────────────────────────────────────

def mutations_allowed() -> bool:
    """Разрешены ли мутации внешнего состояния.

    Принцип P3 из SPEC-001: мутации только явным разрешением.
    Переменная ALLOW_MUTATIONS была объявлена в .env.example, но не читалась
    кодом — теперь читается.
    """
    return os.getenv("ALLOW_MUTATIONS", "0").strip().lower() in ("1", "true", "yes", "on")


def max_mutation_micros() -> int:
    """Потолок одной мутации в микросах (0 = не задан)."""
    raw = os.getenv("ADS_MAX_MUTATION_MICROS", "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def check_mutation_allowed(verdict: Verdict, step: str, amount_micros: int = 0) -> bool:
    """Проверка всех ограничений перед мутацией. False = мутацию выполнять нельзя."""
    if not mutations_allowed():
        verdict.block(
            step,
            "ALLOW_MUTATIONS != 1 — мутации запрещены (dry-run по умолчанию, SPEC-001 P3)",
        )
        return False
    cap = max_mutation_micros()
    if cap and amount_micros > cap:
        verdict.fail(
            step,
            f"amount_micros={amount_micros} превышает cap={cap} "
            f"(ADS_MAX_MUTATION_MICROS)",
        )
        return False
    # Успешную проверку тоже фиксируем — иначе в аудит-трейле шага нет,
    # и Verdict остаётся UNKNOWN при фактически пройденной проверке.
    cap_note = f", cap={cap}" if cap else ""
    verdict.pass_(
        step,
        f"Мутации разрешены (ALLOW_MUTATIONS=1{cap_note})"
        + (f", amount_micros={amount_micros}" if amount_micros else ""),
    )
    return True


# ── Работа с БД ────────────────────────────────────────────────

def connect_db():
    if not DB_PATH.exists():
        sys.exit(
            f"[!] БД не найдена: {DB_PATH}\n"
            f"    Запусти: python scripts/init_db.py"
        )
    conn = sqlite3.connect(DB_PATH)
    # SQLite не включает внешние ключи по умолчанию — без этой pragma
    # ON DELETE CASCADE в схеме НЕ работает, и удаление api_docs оставляет
    # осиротевшие строки в api_endpoints / guides / change_log.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def resolve_doc_id(conn, source: str) -> int:
    """Ищет doc_id по имени источника. Никогда не полагается на «магические» числа.

    Раньше скрипты использовали жёсткие doc_id (1, 2, 3, 6), которые
    соответствовали документам ДРУГИХ источников — аудит-трейл вёлся
    не туда.
    """
    row = conn.execute(
        "SELECT id FROM api_docs WHERE source = ? ORDER BY id LIMIT 1", (source,)
    ).fetchone()
    if row:
        return row[0]
    # Фолбэк: первый документ (api_docs всегда непуст после init_db + sync)
    row = conn.execute("SELECT id FROM api_docs ORDER BY id LIMIT 1").fetchone()
    return row[0] if row else 1


def log_guide(conn, feature: str, title: str, content: str, tags_json: str) -> bool:
    """Пишет гайд в БД. Возвращает True при успехе.

    Исключения НЕ проглатываются — возвращается False, вызывающий код
    решает, что делать. Раньше `except Exception: pass` прятал любые
    ошибки БД.
    """
    source = SOURCE_BY_FEATURE.get(feature, "google-apis-master")
    try:
        doc_id = resolve_doc_id(conn, source)
        conn.execute(
            """INSERT OR IGNORE INTO guides (doc_id, guide_type, title, content, tags)
               VALUES (?, ?, ?, ?, ?)""",
            (doc_id, "setup", title, content, tags_json),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"  [DB WARNING] guides write failed for '{title[:50]}': {e}")
        return False
    except Exception as e:  # noqa: BLE001 — не теряем неожиданные сбои
        print(f"  [DB ERROR] guides write failed for '{title[:50]}': {e}")
        return False


def log_guide_safe(feature: str, title: str, content: str, tags_list) -> bool:
    """Обёртка: открывает БД, пишет гайд, закрывает. Ошибка БД не роняет CLI."""
    tags_json = json.dumps(tags_list, ensure_ascii=False)
    conn = None
    try:
        conn = connect_db()
        return log_guide(conn, feature, title, content, tags_json)
    except SystemExit:
        print("  [DB WARNING] wiki.db отсутствует — гайд не записан")
        return False
    finally:
        if conn is not None:
            conn.close()


# ── Валидаторы форматов ────────────────────────────────────────

def validate_property_id(property_id: str):
    """GA4 property ID обязан быть в формате properties/<numeric_id>.

    Возвращает (ok: bool, message: str).
    """
    if not property_id:
        return False, "property_id не задан"
    if not property_id.startswith("properties/"):
        return False, (
            f"property_id='{property_id}' — должен быть вида 'properties/123456789'"
        )
    tail = property_id[len("properties/"):]
    if not tail.isdigit():
        return False, (
            f"property_id='{property_id}' — после 'properties/' должны быть цифры"
        )
    return True, f"property_id корректен: {property_id}"


def validate_budget_micros(amount_micros: int):
    """Бюджет обязан быть в микросах (не в долларах).

    Возвращает (ok: bool, message: str, warning: str|None).
    """
    if amount_micros < MIN_BUDGET_MICROS:
        return False, (
            f"amount_micros={amount_micros} — меньше $1 ({MIN_BUDGET_MICROS} micros). "
            f"Бюджеты задаются в микросах: $50/день = 50000000"
        ), None
    warning = None
    if amount_micros < WARN_BUDGET_MICROS:
        warning = (
            f"amount_micros={amount_micros} (${amount_micros / 1_000_000:.0f}/день) — "
            f"ниже $10/день; часть типов кампаний такой бюджет отклоняет"
        )
    return True, (
        f"amount_micros={amount_micros} (${amount_micros / 1_000_000:.2f}/день) — "
        f"валидные микросы"
    ), warning


def validate_gaql(query: str):
    """Проверка структуры GAQL: SELECT и FROM обязательны; запрещённые join — нет.

    Возвращает (ok: bool, message: str).
    """
    q = " ".join(query.lower().split())
    if "select" not in q:
        return False, "GAQL без SELECT"
    if "from" not in q:
        return False, "GAQL без FROM"
    if "ad_group_criterion" in q and "search_term_view" in q:
        return False, (
            "запрещённая комбинация: ad_group_criterion + search_term_view "
            "(constraints.md)"
        )
    return True, "SELECT/FROM присутствуют, запрещённых join нет"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
