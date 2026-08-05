def get_claims(filters: Optional[dict] = None, user_email: str = None):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    query = "SELECT claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, date_filed, last_updated FROM claims_history WHERE 1=1"
    params = []
    # Resolve user_email from parameter or filters dict
    email = user_email if user_email is not None else (filters.get("user_email") if filters else None)
    if email:
        query += " AND client = ?"
        params.append(email)
    if filters:
        if filters.get("claim_ref"):
            query += " AND claim_ref LIKE ?"
            params.append(f"%{filters['claim_ref']}%")
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        if filters.get("claim_type"):
            query += " AND claim_type = ?"
            params.append(filters["claim_type"])
    query += " ORDER BY date_filed DESC LIMIT 200"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
