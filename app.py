import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit.components.v1 as components

# =========================
# GOOGLE SHEETS AUTH
# =========================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    dict(st.secrets["gcp_service_account"]),
    scopes=scope
)

client = gspread.authorize(creds)

inventory_sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1dgidhq3iIr2Vt_kxT8VxjU2OrOWzsC39we_AicOR2Gk"
).worksheet("Inventory")

history_sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1dgidhq3iIr2Vt_kxT8VxjU2OrOWzsC39we_AicOR2Gk"
).worksheet("History")

# =========================
# SESSION STATE
# =========================
if "mode" not in st.session_state:
    st.session_state.mode = "home"

if "employee" not in st.session_state:
    st.session_state.employee = ""

if "cart" not in st.session_state:
    st.session_state.cart = []

if "qr" not in st.session_state:
    st.session_state.qr = ""

# =========================
# HELPERS
# =========================
def reset_session():
    st.session_state.employee = ""
    st.session_state.cart = []
    st.session_state.qr = ""
    st.session_state.mode = "home"

def find_row(asset_id):
    data = inventory_sheet.get_all_records()

    for i, row in enumerate(data, start=2):
        if str(row["AssetID"]).strip() == str(asset_id).strip():
            return i, row

    return None, None

def add_history(action, asset_id, employee=""):
    history_sheet.append_row([
        str(datetime.now()),
        action,
        asset_id,
        employee
    ])

# =========================
# QR SCANNER (HTML5 PRO)
# =========================
def qr_scanner():
    scanner_html = """
    <script src="https://unpkg.com/html5-qrcode"></script>

    <div id="reader" style="width:100%;"></div>

    <script>

    function onScanSuccess(decodedText) {
        window.parent.postMessage({
            type: "streamlit:setComponentValue",
            value: decodedText
        }, "*");
    }

    const html5QrcodeScanner = new Html5QrcodeScanner(
        "reader",
        {
            fps: 10,
            qrbox: 250,
            facingMode: { exact: "environment" }  // 🔥 cámara trasera
        }
    );

    html5QrcodeScanner.render(onScanSuccess);

    </script>
    """
    return components.html(scanner_html, height=400)

# =========================
# HOME
# =========================
if st.session_state.mode == "home":

    st.title("🔧 Asset Management System")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📤 CHECKOUT"):
            st.session_state.mode = "checkout"

    with col2:
        if st.button("📥 CHECKIN"):
            st.session_state.mode = "checkin"

# =========================
# CHECKOUT MODE
# =========================
elif st.session_state.mode == "checkout":

    st.title("📤 Checkout Mode")

    st.session_state.employee = st.text_input("Employee Name", st.session_state.employee)

    st.subheader("📷 Scan QR Code")
    qr_value = qr_scanner()

    # recibir QR del scanner
    if qr_value:
        st.session_state.qr = qr_value

    # procesar QR
    if st.session_state.qr:
        code = st.session_state.qr

        row_index, item = find_row(code)

        if not item:
            st.error(f"{code} not found")

        elif item["Status"] != "Available":
            st.warning(f"{code} is {item['Status']}")

        else:
            if code not in st.session_state.cart:
                st.session_state.cart.append(code)
                st.success(f"Added {code}")

        st.session_state.qr = ""

    # CART
    st.subheader("📦 Current Session")
    st.write(st.session_state.cart)

    if st.button("Process Checkout"):

        if not st.session_state.employee:
            st.error("Employee required")
            st.stop()

        for asset in st.session_state.cart:

            row_index, item = find_row(asset)

            if row_index:
                inventory_sheet.update_cell(row_index, 9, "Checked Out")
                inventory_sheet.update_cell(row_index, 11, st.session_state.employee)

                add_history("Checkout", asset, st.session_state.employee)

        st.success("✅ Checkout completed")

    if st.button("Done"):
        reset_session()
        st.rerun()

# =========================
# CHECKIN MODE
# =========================
elif st.session_state.mode == "checkin":

    st.title("📥 Checkin Mode")

    st.info("Escaneo disponible en siguiente versión (ya tienes base lista)")

    if st.button("Done"):
        reset_session()
        st.rerun()