# Databricks notebook source
# DBTITLE 1,Step 1 — Grant USE CATALOG
# MAGIC %sql
# MAGIC GRANT USE CATALOG ON CATALOG main TO `cd29362c-8a09-4a49-927c-92a113f01a70`

# COMMAND ----------

# DBTITLE 1,Step 2 — Grant schema and table access
# MAGIC %sql
# MAGIC GRANT USE SCHEMA ON SCHEMA main.claims TO `cd29362c-8a09-4a49-927c-92a113f01a70`

# COMMAND ----------

# DBTITLE 1,Step 3 — Grant all table privileges
# MAGIC %sql
# MAGIC GRANT SELECT, MODIFY ON TABLE main.claims.fnol_submissions TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT, MODIFY ON TABLE main.claims.assignments      TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT, MODIFY ON TABLE main.claims.status_history   TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT, MODIFY ON TABLE main.claims.client_messages  TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT ON TABLE main.claims.vendors        TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT ON TABLE main.claims.audit_log      TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT ON TABLE main.claims.legal_disputes TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT USE CATALOG ON CATALOG workspace TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT USE SCHEMA ON SCHEMA workspace.default TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT ON TABLE workspace.default.claims_silver         TO `cd29362c-8a09-4a49-927c-92a113f01a70`;
# MAGIC GRANT SELECT ON TABLE workspace.default.claims_gold_monthly   TO `cd29362c-8a09-4a49-927c-92a113f01a70`

# COMMAND ----------

# DBTITLE 1,Step 4 — Verify grants on schema
# MAGIC %sql
# MAGIC SHOW GRANTS ON SCHEMA main.claims

# COMMAND ----------

# DBTITLE 1,Step 5 — Deploy updated app
import subprocess
result = subprocess.run(
    [
        "databricks", "apps", "deploy", "claims-client-portal",
        "--source-code-path", "/Workspace/Users/murachiakiarii@gmail.com/claims-client-portal",
        "--output", "JSON",
    ],
    capture_output=True, text=True,
)
print(result.stdout or result.stderr)

# COMMAND ----------


