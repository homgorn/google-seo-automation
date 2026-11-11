# Скрипт проверки на секреты перед коммитом.
# Запуск: python scripts/secret_scan.py
# Код выхода 0 = чисто, 1 = найдены подозрительные строки.

import os
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent
# Сканируем КОРЕНЬ репозитория, а не только project/.
# Раньше ROOT = project/, и корневой .env / .github/ / docs/ не проверялись —
# реальная дыра: секрет, положенный в корень репо, проходил молча.
# Если project/ лежит не в корне (например, репозиторий вложен), берём parent.
REPO_ROOT = PROJECT_ROOT.parent if PROJECT_ROOT.parent.name else PROJECT_ROOT
if not (REPO_ROOT / ".git").exists() and (PROJECT_ROOT / ".git").exists():
    REPO_ROOT = PROJECT_ROOT
ROOT = Path(os.environ.get("SECRET_SCAN_ROOT", REPO_ROOT)).resolve()

# Ключи/токены по типам (список расширен по результатам ревью 2026-11-11)
HARD_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"ya29\.[A-Za-z0-9_-]{30,}", "Google OAuth token"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI-подобный ключ"),
    (r"sk_live_[A-Za-z0-9]{16,}", "Stripe live secret"),
    (r"pk_live_[A-Za-z0-9]{16,}", "Stripe live publishable"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", "SendGrid key"),
    (r"SK[0-9a-fA-F]{32}", "Twilio key"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Приватный ключ"),
    (r"wJalrXUtnFEMI/K7MDENG/bPxRfiCY", "AWS secret key"),
    (r"(?i)Bearer\s+[A-Za-z0-9._\-]{30,}", "Bearer token"),
    (r"-----BEGIN OPENSSH PRIVATE KEY-----", "SSH private key"),
]

# Строки вида KEY=value / "key": "value" с длинным значением
ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|token|refresh[_-]?token|"
    r"client[_-]?secret|private[_-]?key|credential|auth[_-]?token)\b\s*[=:]\s*[\"']?([A-Za-z0-9_\-./+=]{16,})"
)

PLACEHOLDERS = {
    "", "your", "none", "null", "changeme", "example", "placeholder",
    "xxx", "todo", "your_key_here", "your-key", "yourkey",
    "test", "demo", "sample", "fake", "dummy", "mock", "dev", "local",
    "placeholder_key", "redacted", "hidden", "masked", "notset",
}

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "data", ".venv"}
SKIP_EXT = {".db", ".png", ".jpg", ".ico", ".woff", ".woff2", ".pdf"}
# Сканер не должен находить сам себя: его исходник содержит текст всех
# паттернов. Файл исключается целиком.
SELF_FILENAMES = {"secret_scan.py"}


def looks_like_placeholder(value: str) -> bool:
    """True — значение точно совпадает с плейсхолдером.

    Раньше проверка `"your" in value` маскировала реальные секреты вида
    `your_actual_prod_key_abc123` — подстрочное совпадение вместо точного
    было дырой в сканере.
    """
    v = value.lower()
    if v in PLACEHOLDERS:
        return True
    # Значение целиком состоит из повторов одного маркера (xxxxx, 0000)
    stripped = v.replace("_", "").replace("-", "")
    return bool(stripped) and set(stripped) <= {"x", "0"}


def main() -> int:
    findings = []
    scanned = 0

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.suffix.lower() in SKIP_EXT:
            continue
        if path.name in SELF_FILENAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue

        scanned += 1
        rel = path.relative_to(ROOT)

        for pat, label in HARD_PATTERNS:
            for m in re.finditer(pat, text):
                line = text[: m.start()].count("\n") + 1
                findings.append((rel, line, label, m.group(0)[:12] + "…"))

        for m in ASSIGN_RE.finditer(text):
            value = m.group(2)
            if looks_like_placeholder(value):
                continue
            line = text[: m.start()].count("\n") + 1
            findings.append((rel, line, f"{m.group(1)}=", value[:12] + "…"))

    print(f"Просканировано файлов: {scanned}")

    if not findings:
        print("[OK] Подозрительных секретов не найдено.")
        return 0

    print(f"\n[!] Найдено {len(findings)} подозрительных мест:\n")
    for rel, line, label, sample in findings:
        print(f"  {rel}:{line}  [{label}]  {sample}")

    print(
        "\nЕсли это ложные срабатывания (например, пример в документации) —\n"
        "добавь исключение в SKIP или в PLACEHOLDERS."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())