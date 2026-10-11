# Скрипт проверки на секреты перед коммитом.
# Запуск: python scripts/secret_scan.py
# Код выхода 0 = чисто, 1 = найдены подозрительные строки.

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

ROOT = Path(__file__).parent.parent

# Ключи вида AKIA..., ghp_/gho_/ghs_, ya29., AIza..., sk-...
HARD_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"ya29\.[A-Za-z0-9_-]{30,}", "Google OAuth token"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI-подобный ключ"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Приватный ключ"),
]

# Строки вида KEY=value / "key": "value" с длинным значением
ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|token|refresh[_-]?token|"
    r"client[_-]?secret|private[_-]?key)\b\s*[=:]\s*[\"']?([A-Za-z0-9_\-./+=]{16,})"
)

PLACEHOLDERS = {
    "", "your", "none", "null", "changeme", "example", "placeholder",
    "xxx", "todo", "your_key_here", "your-key", "yourkey",
}

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "data", ".venv"}
SKIP_EXT = {".db", ".png", ".jpg", ".ico", ".woff", ".woff2", ".pdf"}


def looks_like_placeholder(value: str) -> bool:
    v = value.lower()
    if v in PLACEHOLDERS:
        return True
    if "your" in v or "example" in v or "changeme" in v:
        return True
    # Шаблон .env: пустое значение — норма
    return False


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