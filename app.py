import streamlit as st
import requests
import json

# Page Configuration
st.set_page_config(
    page_title="GA-IDP Gateway — Prototype Control Center",
    page_icon="🛡️",
    layout="wide"
)

# Sidebar for Configuration & Authentication
st.sidebar.header("Gateway Settings")
API_URL = st.sidebar.text_input("FastAPI Base URL", value="http://127.0.0.1:8000")
API_KEY = st.sidebar.text_input("X-API-Key", value="demo-key-change-me", type="password")

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

st.title("🛡️ GA-IDP Gateway — Prototype Control Center")
st.markdown("Intelligent Document Processing (IDP) & RPA Middleware Layer for GA Insurance Limited.")

# Tabs representing the 4-Tier Blueprint architecture
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Tier 1 & 2: Intake & Extraction", 
    "⚖️ Tier 3: Validation & HITL", 
    "⚙️ Tier 4: Core Connectors", 
    "📊 Audit Trail"
])

with tab1:
    st.subheader("Tier 1 & 2: Unstructured Document Ingestion & OCR Extraction")
    st.markdown("Simulates multi-source ingestion and AI parsing/OCR normalization into structured JSON.")
    
    raw_text_input = st.text_area(
        "Raw Document Text", 
        value="Name: Jane Wanjiku ID: 32145678 Policy: Life Assurance Phone: 0722334455"
    )
    doc_type = st.selectbox("Document Type", ["registration_form", "claim_form", "policy_schedule"])
    
    if st.button("Process & Extract Document"):
        with st.spinner("Processing through IDP pipeline..."):
            try:
                response = requests.post(
                    f"{API_URL}/api/v1/extract-registration",
                    headers=headers,
                    json={"raw_text": raw_text_input, "document_type": doc_type},
                    timeout=10
                )
                if response.status_code == 200:
                    res_data = response.json()
                    st.success("Document parsed and evaluated successfully!")
                    st.json(res_data)
                    st.session_state["last_validation_result"] = res_data
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to FastAPI backend at `{API_URL}`. Ensure your Uvicorn server is running.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

with tab2:
    st.subheader("Tier 3: Business Validation & Human-in-the-Loop (HITL)")
    st.markdown("Evaluates confidence scoring ($\theta = 0.95$) and routes exceptions to review queues.")
    
    if st.button("Check Open Review Queue"):
        try:
            response = requests.get(f"{API_URL}/review", headers={"X-API-Key": API_KEY}, timeout=10)
            if response.status_code == 200:
                st.info("Access the interactive web review dashboard directly in your browser at:")
                st.markdown(f"👉 [{API_URL}/review]({API_URL}/review)")
            else:
                st.error(f"Error fetching review dashboard: {response.status_code}")
        except Exception as e:
            st.error(f"Connection error: {e}")

with tab3:
    st.subheader("Tier 4: Enterprise System Connectors")
    st.markdown("Pushes validated JSON payloads into target enterprise environments (SAP HANA, Oracle Cloud, or Cloud Warehouses).")
    
    if "last_validation_result" in st.session_state:
        st.write("Current Validated Payload Ready for Dispatch:")
        st.json(st.session_state["last_validation_result"])
        
        target_system = st.selectbox(
            "Select Target Enterprise Backbone", 
            ["sap_hana", "oracle_oic", "snowflake_warehouse"]
        )
        
        if st.button("Push to Enterprise Core"):
            try:
                push_payload = {
                    "validation_result": st.session_state["last_validation_result"],
                    "target": target_system
                }
                response = requests.post(
                    f"{API_URL}/api/v1/push-to-core",
                    headers=headers,
                    json=push_payload,
                    timeout=10
                )
                if response.status_code == 200:
                    st.success("Successfully routed payload to enterprise core system!")
                    st.json(response.json())
                elif response.status_code == 409:
                    st.warning("Blocked (409 Conflict): Payload flagged below threshold; requires HITL resolution before core sync.")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to FastAPI backend at `{API_URL}`.")
            except Exception as e:
                st.error(f"Connection error: {e}")
    else:
        st.info("Process and validate a document in Tier 1 & 2 first to enable core pushing.")

with tab4:
    st.subheader("Immutable Audit Trail & Compliance Logging")
    st.markdown("Maintains continuous auditing and governance tracking for all middleware events.")
    
    if st.button("Fetch Audit Logs"):
        try:
            response = requests.get(f"{API_URL}/api/v1/audit-log", headers=headers, timeout=10)
            if response.status_code == 200:
                logs = response.json()
                st.write(f"Total Logged Events: {logs.get('count', 0)}")
                st.dataframe(logs.get("entries", []))
            else:
                st.error(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to FastAPI backend at `{API_URL}`.")
        except Exception as e:
            st.error(f"Connection error: {e}")
