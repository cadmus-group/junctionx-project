"""Export the FastAPI OpenAPI document to packages/contracts/openapi.json.

Runs without a database connection (only imports the app and reads its schema).
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "domain-py" / "src"))


def main() -> None:
    from gridtrace_api.main import create_app

    app = create_app()
    schema = app.openapi()
    out = ROOT / "packages" / "contracts" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
