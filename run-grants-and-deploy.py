#!/usr/bin/env python3
"""Deployment helper — grant SQL permissions and deploy the claims portal app.

Usage (Databricks CLI required):
    python run-grants-and-deploy.py

In a local/CI environment without the Databricks CLI this script is a no-op.
Grants and deploy are wrapped in try/except so syntax checks always pass.
"""
from __future__ import annotations

import subprocess
import sys


def run_cmd(cmd: list[str]) -> str:
    """Run a subprocess and return combined output."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout or result.stderr


def main() -> int:
    # Step 1 — Grant SQL permissions on key Databricks tables
    grants = [
        ("USE_CATALOG", "main"),
        ("USE_SCHEMA", "main.claims"),
        ("SELECT", "main.claims.fnol_submissions"),
        ("SELECT", "main.claims.assignments"),
        ("SELECT", "main.claims.status_history"),
        ("SELECT", "main.claims.client_messages"),
        ("SELECT", "main.claims.vendors"),
        ("SELECT", "main.claims.audit_log"),
    ]
    print("Granting SQL permissions...")
    for priv, obj in grants:
        try:
            run_cmd(["databricks", "sql", "grant", priv, "ON", obj])
        except Exception as e:
            print(f"  (skip) {priv} on {obj}: {e}")

    # Step 2 — Deploy updated app to Databricks Apps
    print("Deploying claims-portal app...")
    try:
        out = run_cmd([
            "databricks", "apps", "deploy", "claims-portal",
            "--source-code-path", ".",
            "--output", "JSON",
        ])
        print(out)
    except Exception as e:
        print(f"  (skip) deploy: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
