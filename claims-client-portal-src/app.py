import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime, date, time, timedelta
from databricks import sql
from databricks.sdk.core import Config
import math

# ============================================================================
# PAGE CONFIG & STYLE
# ============================================================================

st.set_page_config(
    page_title="Claims Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for branded styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Header brand bar */
    .main-header {
        background: #0A1628;
        color: white;
        padding: 1.5rem 2rem;
        margin: -1rem -2rem 2rem -2rem;
        border-radius: 0;
    }
    
    .main-header h1 {
        margin: 0;
        font-weight: 600;
        font-size: 1.8rem;
    }
    
    .main-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    /* Status badges */
    .status-badge {
        padding: 0.4rem 1rem;
        border-radius: 1rem;
        font-weight: 500;
        font-size: 0.85rem;
        display: inline-block;
        margin: 0.25rem 0;
    }
    
    .status-submitted { background: #E3F2FD; color: #0D47A1; }
    .status-under-assessment { background: #FFF9C4; color: #F57C00; }
    .status-approved { background: #C8E6C9; color: #2E7D32; }
    .status-settled { background: #C8E6C9; color: #1B5E20; }
    .status-rejected { background: #FFCDD2; color: #C62828; }
    
    /* Claim cards */
    .claim-card {
        background: white;
        border: 1px solid #E0E0E0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .claim-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-color: #1E88E5;
    }
    
    /* Accent blue for interactive elements */
    .stButton>button {
        background: #1E88E5;
        color: white;
        border: none;
        border-radius: 0.3rem;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    
    .stButton>button:hover {
        background: #1565C0;
    }
    
    /* Timeline stepper */
    .stepper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 2rem 0;
    }
    
    .stepper-step {
        flex: 1;
        text-align: center;
        position: relative;
    }
    
    .stepper-circle {
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 50%;
        margin: 0 auto 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .stepper-circle.active {
        background: #1E88E5;
        color: white;
    }
    
    .stepper-circle.completed {
        background: #4CAF50;
        color: white;
    }
    
    .stepper-circle.pending {
        background: #E0E0E0;
        color: #757575;
    }
    
    .stepper-label {
        font-size: 0.85rem;
        color: #424242;
    }
    
    /* Notification list */
    .notification-item {
        padding: 1rem;
        border-left: 3px solid #1E88E5;
        background: #F5F5F5;
        margin-bottom: 0.75rem;
        border-radius: 0.25rem;
    }
    
    .notification-item.unread {
        background: #E3F2FD;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

cfg = Config()
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

def get_connection():
    """Get authenticated database connection using app service principal."""
    server_hostname = cfg.host
    if server_hostname.startswith('https://'):
        server_hostname = server_hostname.replace('https://', '')
    elif server_hostname.startswith('http://'):
        server_hostname = server_hostname.replace('http://', '')
    
    http_path = f"/sql/1.0/warehouses/{WAREHOUSE_ID}"
    
    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
        _use_arrow_native_complex_types=False,
    )

def run_query(query: str, params: dict = None) -> pd.DataFrame:
    """Execute SQL query and return pandas DataFrame."""
    conn = get_connection()
    with conn.cursor() as cursor:
        if params:
            # For parameterized queries
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        try:
            return cursor.fetchall_arrow().to_pandas()
        except:
            # For non-SELECT queries
            return pd.DataFrame()

def run_insert(table: str, df: pd.DataFrame):
    """Insert rows into table using INSERT VALUES."""
    if df.empty:
        return
    
    conn = get_connection()
    with conn.cursor() as cursor:
        rows = list(df.itertuples(index=False))
        
        def format_value(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return 'NULL'
            elif isinstance(val, str):
                return repr(val)
            elif isinstance(val, (date, datetime)):
                return f"'{val}'"
            else:
                return str(val)
        
        values = ", ".join([f"({','.join(map(format_value, row))})" for row in rows])
        cursor.execute(f"INSERT INTO {table} VALUES {values}")

def audit_log(action: str, details: str):
    """Log user action to portal_audit_log."""
    if 'policy_id' not in st.session_state or 'customer_id' not in st.session_state:
        return
    
    df = pd.DataFrame([{
        'event_ts': datetime.now(),
        'user_id': st.session_state.customer_id,
        'policy_id': st.session_state.policy_id,
        'action': action,
        'details': details,
        'ip_address': 'APP'
    }])
    run_insert('workspace.default.portal_audit_log', df)

# ============================================================================
# TABLE INITIALIZATION
# ============================================================================

def init_tables():
    """Create supporting tables if they don't exist."""
    conn = get_connection()
    with conn.cursor() as cursor:
        # claims_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace.default.claims_documents (
                claim_id STRING,
                filename STRING,
                doc_type STRING,
                file_size_kb DOUBLE,
                upload_ts TIMESTAMP,
                uploaded_by STRING
            )
        """)
        
        # portal_audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace.default.portal_audit_log (
                event_ts TIMESTAMP,
                user_id STRING,
                policy_id STRING,
                action STRING,
                details STRING,
                ip_address STRING
            )
        """)
        
        # claims_alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace.default.claims_alerts (
                alert_id STRING,
                customer_id STRING,
                policy_id STRING,
                claim_id STRING,
                alert_type STRING,
                message STRING,
                created_at TIMESTAMP,
                is_read BOOLEAN
            )
        """)

# Run initialization once
if 'tables_initialized' not in st.session_state:
    try:
        init_tables()
        st.session_state.tables_initialized = True
    except Exception as e:
        st.error(f"Failed to initialize tables: {e}")

# ============================================================================
# AUTHENTICATION
# ============================================================================

def login_page():
    """3-field authentication page."""
    st.markdown('<div class="main-header"><h1>🛡️ Motor Insurance Claims Portal</h1><p>Client Self-Service Portal</p></div>', unsafe_allow_html=True)
    
    st.markdown("### Welcome")
    st.write("Please authenticate using your policy details:")
    
    with st.form("login_form"):
        policy_number = st.text_input("Policy Number", placeholder="POL123456")
        id_passport = st.text_input("ID/Passport Number", placeholder="12345678")
        vehicle_reg = st.text_input("Vehicle Registration Number", placeholder="KAA123B")
        
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not policy_number or not id_passport or not vehicle_reg:
                st.error("All fields are required.")
                return
            
            # Query claims_silver for matching policy
            query = """
                SELECT DISTINCT policy_id, customer_id, vehicle_vin
                FROM workspace.default.claims_silver
                WHERE policy_id = :policy_id
                LIMIT 1
            """
            
            try:
                df = run_query(query, {'policy_id': policy_number})
                
                if not df.empty:
                    # Simplified validation: just check policy exists
                    # In production, would validate ID/Passport and Vehicle Reg
                    st.session_state.authenticated = True
                    st.session_state.policy_id = df.iloc[0]['policy_id']
                    st.session_state.customer_id = df.iloc[0]['customer_id']
                    audit_log('login', f'User logged in: {policy_number}')
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please check your policy number and try again.")
            except Exception as e:
                st.error(f"Authentication error: {e}")

def logout():
    """Clear session and return to login."""
    audit_log('logout', 'User logged out')
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ============================================================================
# PAGE: MY CLAIMS
# ============================================================================

def page_my_claims():
    """Display all claims for authenticated policy."""
    st.markdown(f"### My Claims")
    st.write(f"Policy: {st.session_state.policy_id}")
    
    query = """
        SELECT 
            claim_id,
            claim_date,
            claim_type,
            claim_status,
            damage_amount,
            net_claim_amount,
            claim_severity,
            vehicle_make,
            vehicle_model,
            vehicle_year,
            state,
            adjuster_id,
            repair_shop
        FROM workspace.default.claims_silver
        WHERE policy_id = :policy_id
        ORDER BY claim_date DESC
    """
    
    df = run_query(query, {'policy_id': st.session_state.policy_id})
    
    if df.empty:
        st.info("You have no claims on record. Use 'File a New Claim' to submit a claim.")
        return
    
    status_colors = {
        'Submitted': 'submitted',
        'Under Assessment': 'under-assessment',
        'Approved for Repair': 'approved',
        'Settled': 'settled',
        'Rejected': 'rejected'
    }
    
    for idx, row in df.iterrows():
        status_class = status_colors.get(row['claim_status'], 'submitted')
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**Claim ID:** {row['claim_id']}")
                st.caption(f"Date: {row['claim_date']}")
            
            with col2:
                st.markdown(f"**Type:** {row['claim_type']}")
                st.caption(f"Severity: {row['claim_severity']}")
            
            with col3:
                st.markdown(f'<span class="status-badge status-{status_class}">{row["claim_status"]}</span>', unsafe_allow_html=True)
            
            with col4:
                st.metric("Damage", f"KES {row['damage_amount']:,.0f}")
            
            with st.expander("📄 View Details"):
                details_col1, details_col2 = st.columns(2)
                
                with details_col1:
                    st.write(f"**Vehicle:** {row['vehicle_year']} {row['vehicle_make']} {row['vehicle_model']}")
                    st.write(f"**Location:** {row['state']}")
                    st.write(f"**Adjuster ID:** {row['adjuster_id']}")
                
                with details_col2:
                    st.write(f"**Damage Amount:** KES {row['damage_amount']:,.2f}")
                    st.write(f"**Net Claim Amount:** KES {row['net_claim_amount']:,.2f}")
                    st.write(f"**Repair Shop:** {row['repair_shop'] if pd.notna(row['repair_shop']) else 'Not assigned'}")
            
            st.markdown("---")
    
    audit_log('view_claims', f'Viewed {len(df)} claims')

# ============================================================================
# PAGE: FILE A NEW CLAIM (FNOL)
# ============================================================================

def page_file_claim():
    """First Notice of Loss form."""
    st.markdown("### File a New Claim (FNOL)")
    st.write("Please provide complete incident details.")
    
    with st.form("fnol_form"):
        st.subheader("Incident Details")
        col1, col2 = st.columns(2)
        
        with col1:
            incident_date = st.date_input("Incident Date", max_value=date.today())
            incident_time = st.time_input("Incident Time")
            street = st.text_input("Street/Road")
            city = st.text_input("City")
        
        with col2:
            county = st.text_input("County")
            claim_type = st.selectbox("Claim Type", [
                "Collision",
                "Theft",
                "Vandalism",
                "Weather Damage",
                "Fire",
                "Other"
            ])
            estimated_damage = st.number_input("Estimated Damage Amount (KES)", min_value=0.0, step=1000.0)
        
        description = st.text_area(
            "Incident Description",
            placeholder="Describe what happened in detail (minimum 50 characters)...",
            height=120
        )
        
        st.subheader("Third-Party Involvement")
        third_party = st.checkbox("Third-party involved?")
        third_party_details = ""
        if third_party:
            third_party_details = st.text_area("Third-party details", height=80)
        
        st.subheader("Police Report")
        police_reported = st.checkbox("Reported to police?")
        police_ref = ""
        if police_reported:
            police_ref = st.text_input("Police Reference/OB Number")
        
        st.subheader("Document Upload")
        st.caption("📎 Please prepare: Driver's License (required), Police Abstract (if reported), NTSA Logbook (required), Scene Photos (optional), Other supporting documents (optional)")
        
        drivers_license = st.file_uploader("Driver's License (Required)", type=['pdf', 'jpg', 'jpeg', 'png'])
        police_abstract = st.file_uploader("Police Abstract", type=['pdf', 'jpg', 'jpeg', 'png']) if police_reported else None
        ntsa_logbook = st.file_uploader("NTSA Logbook (Required)", type=['pdf', 'jpg', 'jpeg', 'png'])
        scene_photos = st.file_uploader("Scene Photos (Optional, up to 5)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        other_docs = st.file_uploader("Other Documents (Optional)", type=['pdf', 'jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        submitted = st.form_submit_button("Submit Claim", use_container_width=True)
        
        if submitted:
            # Validation
            errors = []
            if len(description) < 50:
                errors.append("Description must be at least 50 characters.")
            if not drivers_license:
                errors.append("Driver's License is required.")
            if not ntsa_logbook:
                errors.append("NTSA Logbook is required.")
            if police_reported and not police_abstract:
                errors.append("Police Abstract is required when incident was reported to police.")
            if estimated_damage <= 0:
                errors.append("Estimated damage must be greater than 0.")
            
            if errors:
                for err in errors:
                    st.error(err)
                return
            
            # Generate claim ID
            claim_id = str(uuid.uuid4())
            
            # Insert into claims_bronze
            incident_datetime = datetime.combine(incident_date, incident_time)
            report_datetime = datetime.now()
            
            claim_data = pd.DataFrame([{
                'claim_id': claim_id,
                'policy_id': st.session_state.policy_id,
                'customer_id': st.session_state.customer_id,
                'claim_date': str(incident_date),
                'report_date': str(report_datetime.date()),
                'claim_type': claim_type,
                'claim_status': 'Submitted',
                'vehicle_year': None,
                'vehicle_make': None,
                'vehicle_model': None,
                'vehicle_vin': None,
                'state': county,
                'damage_amount': float(estimated_damage),
                'deductible': None,
                'adjuster_id': None,
                'repair_shop': None,
                'is_suspicious_flag': False,
                'ingestion_ts': str(report_datetime),
                'source_system': 'CLIENT_PORTAL'
            }])
            
            try:
                run_insert('workspace.default.claims_bronze', claim_data)
                
                # Log document metadata
                docs = []
                if drivers_license:
                    docs.append({
                        'claim_id': claim_id,
                        'filename': drivers_license.name,
                        'doc_type': 'drivers_license',
                        'file_size_kb': drivers_license.size / 1024,
                        'upload_ts': datetime.now(),
                        'uploaded_by': st.session_state.customer_id
                    })
                if ntsa_logbook:
                    docs.append({
                        'claim_id': claim_id,
                        'filename': ntsa_logbook.name,
                        'doc_type': 'ntsa_logbook',
                        'file_size_kb': ntsa_logbook.size / 1024,
                        'upload_ts': datetime.now(),
                        'uploaded_by': st.session_state.customer_id
                    })
                if police_abstract:
                    docs.append({
                        'claim_id': claim_id,
                        'filename': police_abstract.name,
                        'doc_type': 'police_abstract',
                        'file_size_kb': police_abstract.size / 1024,
                        'upload_ts': datetime.now(),
                        'uploaded_by': st.session_state.customer_id
                    })
                if scene_photos:
                    for photo in scene_photos[:5]:
                        docs.append({
                            'claim_id': claim_id,
                            'filename': photo.name,
                            'doc_type': 'scene_photo',
                            'file_size_kb': photo.size / 1024,
                            'upload_ts': datetime.now(),
                            'uploaded_by': st.session_state.customer_id
                        })
                if other_docs:
                    for doc in other_docs:
                        docs.append({
                            'claim_id': claim_id,
                            'filename': doc.name,
                            'doc_type': 'other',
                            'file_size_kb': doc.size / 1024,
                            'upload_ts': datetime.now(),
                            'uploaded_by': st.session_state.customer_id
                        })
                
                if docs:
                    docs_df = pd.DataFrame(docs)
                    run_insert('workspace.default.claims_documents', docs_df)
                
                audit_log('submit_claim', f'Submitted new claim: {claim_id}')
                
                st.success(f"✅ Claim submitted successfully! Your claim ID is: **{claim_id}**")
                st.info("Your claim will be reviewed within 2 business days. You can track its status in the 'Claim Status Tracker' page.")
                
            except Exception as e:
                st.error(f"Failed to submit claim: {e}")

# ============================================================================
# PAGE: CLAIM STATUS TRACKER
# ============================================================================

def page_status_tracker():
    """Visual timeline of claim progression."""
    st.markdown("### Claim Status Tracker")
    
    query = """
        SELECT claim_id, claim_date, claim_type, claim_status, damage_amount
        FROM workspace.default.claims_silver
        WHERE policy_id = :policy_id
        ORDER BY claim_date DESC
    """
    
    df = run_query(query, {'policy_id': st.session_state.policy_id})
    
    if df.empty:
        st.info("No claims to track.")
        return
    
    claim_options = [f"{row['claim_id']} ({row['claim_type']} - {row['claim_date']})" for _, row in df.iterrows()]
    selected = st.selectbox("Select Claim", claim_options)
    
    if not selected:
        return
    
    selected_claim_id = selected.split(" ")[0]
    claim_row = df[df['claim_id'] == selected_claim_id].iloc[0]
    current_status = claim_row['claim_status']
    
    # Define milestones
    milestones = [
        "Submitted",
        "Under Assessment",
        "Approved for Repair",
        "Settled"
    ]
    
    sla_days = {
        "Submitted": 2,
        "Under Assessment": 5,
        "Approved for Repair": 10
    }
    
    # Determine active milestone
    if current_status == "Rejected":
        st.error(f"❌ This claim has been **Rejected**.")
        return
    
    try:
        current_index = milestones.index(current_status)
    except ValueError:
        current_index = 0
    
    # Render stepper
    st.markdown('<div class="stepper">', unsafe_allow_html=True)
    
    for i, milestone in enumerate(milestones):
        if i < current_index:
            circle_class = "completed"
            icon = "✓"
        elif i == current_index:
            circle_class = "active"
            icon = str(i + 1)
        else:
            circle_class = "pending"
            icon = str(i + 1)
        
        st.markdown(f"""
            <div class="stepper-step">
                <div class="stepper-circle {circle_class}">{icon}</div>
                <div class="stepper-label">{milestone}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # SLA info
    if current_status in sla_days:
        st.info(f"⏱️ SLA: {sla_days[current_status]} business days remaining for current stage.")
    
    audit_log('track_status', f'Tracked status for claim: {selected_claim_id}')

# ============================================================================
# PAGE: NOTIFICATIONS
# ============================================================================

def page_notifications():
    """Display user notifications."""
    st.markdown("### Notifications")
    
    query = """
        SELECT alert_id, claim_id, alert_type, message, created_at, is_read
        FROM workspace.default.claims_alerts
        WHERE customer_id = :customer_id
        ORDER BY created_at DESC
        LIMIT 50
    """
    
    df = run_query(query, {'customer_id': st.session_state.customer_id})
    
    if df.empty:
        st.info("No notifications.")
        return
    
    for _, row in df.iterrows():
        read_class = "" if row['is_read'] else "unread"
        read_indicator = "" if row['is_read'] else "🔵 "
        
        st.markdown(f"""
            <div class="notification-item {read_class}">
                <strong>{read_indicator}{row['alert_type']}</strong><br>
                {row['message']}<br>
                <small>Claim: {row['claim_id']} | {row['created_at']}</small>
            </div>
        """, unsafe_allow_html=True)
    
    audit_log('view_notifications', f'Viewed {len(df)} notifications')

# ============================================================================
# PAGE: MY PROFILE
# ============================================================================

def page_profile():
    """Display policy and user statistics."""
    st.markdown("### My Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Policy Information")
        st.write(f"**Policy ID:** {st.session_state.policy_id}")
        st.write(f"**Customer ID:** {st.session_state.customer_id}")
    
    with col2:
        st.markdown("#### Claims Summary")
        
        query = """
            SELECT 
                COUNT(*) as total_claims,
                SUM(damage_amount) as total_damage,
                AVG(CASE WHEN claim_status IN ('Approved for Repair', 'Settled') THEN 1.0 ELSE 0.0 END) as approval_rate
            FROM workspace.default.claims_silver
            WHERE policy_id = :policy_id
        """
        
        df = run_query(query, {'policy_id': st.session_state.policy_id})
        
        if not df.empty:
            st.metric("Total Claims", int(df.iloc[0]['total_claims']))
            st.metric("Total Damage", f"KES {df.iloc[0]['total_damage']:,.0f}")
            st.metric("Approval Rate", f"{df.iloc[0]['approval_rate']*100:.1f}%")
    
    st.markdown("---")
    st.markdown("#### Contact Support")
    st.info("""
        📞 **Hotline:** +254 700 123 456  
        📧 **Email:** claims@motorinsurance.co.ke  
        ⏰ **Hours:** Monday - Friday, 8:00 AM - 5:00 PM  
    """)
    
    audit_log('view_profile', 'Viewed profile page')

# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    # Check authentication
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        login_page()
        return
    
    # Sidebar navigation
    st.sidebar.markdown("### Navigation")
    st.sidebar.markdown(f"**Welcome, Customer ID:** {st.session_state.customer_id}")
    st.sidebar.markdown(f"**Policy:** {st.session_state.policy_id}")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Go to:",
        ["My Claims", "File a New Claim", "Claim Status Tracker", "Notifications", "My Profile"]
    )
    
    if st.sidebar.button("Logout", use_container_width=True):
        logout()
    
    # Render header
    st.markdown('<div class="main-header"><h1>🛡️ Motor Insurance Claims Portal</h1><p>Client Self-Service Portal</p></div>', unsafe_allow_html=True)
    
    # Route to selected page
    if page == "My Claims":
        page_my_claims()
    elif page == "File a New Claim":
        page_file_claim()
    elif page == "Claim Status Tracker":
        page_status_tracker()
    elif page == "Notifications":
        page_notifications()
    elif page == "My Profile":
        page_profile()

if __name__ == "__main__":
    main()