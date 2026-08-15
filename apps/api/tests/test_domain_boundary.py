"""Enforces: domain code must not import fastapi or sqlalchemy.

Grep-based on purpose, per the plan's "kept deliberately light" verification
note — no import-linter dependency needed for a two-package boundary.
"""

from pathlib import Path

DOMAIN_DIR = Path(__file__).resolve().parents[1] / "src" / "metaforge_api" / "domain"
FORBIDDEN = ("fastapi", "sqlalchemy")


def test_domain_has_no_framework_imports():
    offenders = []
    for path in DOMAIN_DIR.glob("*.py"):
        text = path.read_text()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for forbidden in FORBIDDEN:
                    if forbidden in stripped:
                        offenders.append(f"{path.name}: {stripped}")
    assert not offenders, f"domain/ must not import fastapi/sqlalchemy: {offenders}"
