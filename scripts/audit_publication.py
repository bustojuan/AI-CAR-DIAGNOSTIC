"""Dependency-free checks of publication files; never contacts services or reads .env."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "test-results",
    "playwright-report",
    ".local-tools",
    ".cache",
}
RULES = {
    "OpenAI-like credential": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}",
    "Neon-like password": r"\bnpg_[A-Za-z0-9]{10,}",
    "AWS access key": r"\bAKIA[A-Z0-9]{16}\b",
    "GitHub access token": r"\b(?:ghp|gho)_[A-Za-z0-9]{30,}",
    "developer absolute location": (
        r"(?i)[A-Z]:[\\/]Users[\\/]|/(?:Users|home)/[A-Za-z0-9._-]+/"
    ),
    "personal email": r"(?i)[\w.+-]+@(?:gmail|hotmail|accenture)\.[a-z]+",
    "private Neon endpoint": r"\bep-[a-z0-9-]+\.[a-z0-9.-]+\.neon\.tech\b",
}


def run():
    failures = []
    files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not any(s in EXCLUDED for s in p.relative_to(ROOT).parts)
    ]
    links = 0
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if path.name == ".env" or (
            path.name.startswith(".env.") and path.name != ".env.example"
        ):
            failures.append({"file": relative, "reason": "real environment file"})
        if path.suffix.lower() in {".pdf", ".dump", ".sqlite", ".sqlite3", ".zip"}:
            failures.append({"file": relative, "reason": "private/runtime file type"})
        if path.suffix.lower() in {".glb", ".png", ".jpg", ".jpeg"}:
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            continue
        for name, pattern in RULES.items():
            if re.search(pattern, content):
                failures.append({"file": relative, "reason": name})
        if path.suffix.lower() == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
                target = target.strip("<>").split("#")[0]
                if not target or re.match(r"(?:https?|mailto):", target):
                    continue
                links += 1
                if not (path.parent / target).exists():
                    failures.append(
                        {
                            "file": relative,
                            "reason": "missing relative link",
                            "target": target,
                        }
                    )
    for required in [
        "LICENSE",
        "README.md",
        "backend/pyproject.toml",
        "backend/uv.lock",
        "frontend/package-lock.json",
        "docs/ASSET_CREDITS.md",
        "docs/setup/LOCAL_SETUP.md",
    ]:
        if not (ROOT / required).is_file():
            failures.append(
                {"file": required, "reason": "required publication file missing"}
            )
    return {
        "files_checked": len(files),
        "relative_links_checked": links,
        "findings": failures,
        "scope": "Pattern/link checks; not an exhaustive secret, security or rights guarantee.",
    }


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["findings"] else 0)
