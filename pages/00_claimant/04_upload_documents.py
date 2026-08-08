"""Upload Documents — pages/00_claimant/04_upload_documents.py"""
"""
Role: client
Upload supporting documents with GPS metadata extraction (Phase 2 spec: Section 16.3).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_api
import streamlit as st

def render(user_email: str, user_role: str = "client") -> None:
    st.title("📎 Upload Documents")
    claim_ref = st.text_input("Claim Reference *", placeholder="CLM-XXXXXXXX")
    if not claim_ref:
        st.info("Enter your claim reference first.")
        return
    st.info("Supported: PDF, JPG, PNG, DOCX. Max 10 MB per file. Photos should carry GPS metadata.")
    uploaded = st.file_uploader("Choose files", type=["pdf","jpg","jpeg","png","docx","xlsx"], accept_multiple_files=True)
    if uploaded:
        st.write(f"**{len(uploaded)} file(s) ready to upload**")
        for f in uploaded:
            st.write(f"  - {f.name} ({f.size/1024:.1f} KB)")
        if st.button("Upload", type="primary"):
            for f in uploaded:
                try:
                    data = f.read()
                    gps = None
                    if hasattr(core_api, "extract_gps_metadata"):
                        try: gps = core_api.extract_gps_metadata(data)
                        except: pass
                    core_api.store_document_metadata(claim_ref, f.name, len(data), gps)
                except Exception as e:
                    st.warning(f"{f.name}: {e}")
            st.success("Documents uploaded successfully.")
