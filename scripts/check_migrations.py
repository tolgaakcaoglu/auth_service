import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv


def _latest_migration_file(versions_dir: Path) -> Path:
    migrations = list(versions_dir.glob("*.py"))
    if not migrations:
        raise FileNotFoundError("No migration files found in alembic/versions")
    return max(migrations, key=lambda path: path.stat().st_mtime)


def main() -> None:
    load_dotenv()
    versions_dir = Path("alembic/versions")

    subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", "ci-check"],
        check=True,
    )

    latest = _latest_migration_file(versions_dir)
    content = latest.read_text()
    has_ops = re.search(r"^\s+op\.", content, re.M) is not None
    latest.unlink()

    if has_ops:
        raise SystemExit(
            "Migration drift detected. Generate a migration with "
            "`alembic revision --autogenerate -m \"...\"`."
        )

    print("No migration drift detected.")


if __name__ == "__main__":
    main()
