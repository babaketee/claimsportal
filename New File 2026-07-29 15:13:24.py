# Notebooks are created via the Databricks UI, not through Python code.
# You can use the Databricks REST API to create a notebook programmatically.

import requests

workspace_url = "https://<your-databricks-workspace-url>"
token = "<your-databricks-access-token>"

headers = {
    "Authorization": f"Bearer {token}"
}

data = {
    "path": "/Users/<your-username>/NewNotebook",
    "language": "PY