import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_qrcode_scanner import qrcode_scanner

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Asset Management",
    layout="centered"
)

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

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1dgidhq3iIr2Vt_kxT8VxjU2OrOWzsC39we_AicOR2Gk"

inventory_sheet = client.open_by_url(
    SPREADSHEET_URL
).worksheet("Inventory")

history_sheet = client.open_by_url(
    SPREADSHEET_URL
).worksheet("History")

# =========================
# SESSION STATE
# =========================
defaults = {
    "mode": "home",
    "employee": "",
    "cart": [],
    "last_scanned": ""
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value

# =========================
# HELPERS
# =========================
def reset_session():

    st.session_state.mode = "home"
    st.session_state.employee = ""
    st.session_state.cart = []
    st.session_state.last_scanned = ""

def find_row(asset_id):

    data = inventory_sheet.get_all_records()

    for i, row in enumerate(data, start=2):

        if str(row["AssetID"]).strip() == str(asset_id).strip():

            return i, row

    return None, None

def add_history(action, asset_id, employee="", notes=""):

    history_sheet.append_row([
        str(datetime.now()),
        action,
        asset_id,
        employee,
        notes
    ])

# =========================
# HOME
# =========================
if st.session_state.mode == "home":

    st.title("🔧 Asset Management System")

    col1, col2 = st.columns(2)

    with col1:

        if st.button("📤 CHECKOUT"):

            st.session_state.mode = "checkout"
            st.rerun()

    with col2:

        if st.button("📥 CHECKIN"):

            st.session_state.mode = "checkin"
            st.rerun()

# =========================
# CHECKOUT
# =========================
elif st.session_state.mode == "checkout":

    st.title("📤 Checkout Mode")

    st.text_input(
        "Employee Name",
        key="employee"
    )

    st.subheader("📷 Scan Asset")

    qr_value = qrcode_scanner()

    # =========================
    # PROCESS SCAN
    # =========================
    if (
        qr_value and
        qr_value != st.session_state.last_scanned
    ):

        st.session_state.last_scanned = qr_value

        row_index, item = find_row(qr_value)

        if not item:

            st.error(f"{qr_value} not found")

        elif item["Status"] != "Available":

            st.warning(f"{qr_value} is {item['Status']}")

        else:

            if qr_value not in st.session_state.cart:
                item_name = item["Name"] if item and "Name" in item else "Unknown"
                st.session_state.cart.append({
                    "id": qr_value,
                    "name": item_name
                })
                st.success(f"✅ Added {qr_value} — {item_name}")

    # =========================
    # CURRENT SESSION
    # =========================
    st.subheader("📦 Current Session")

    for item in st.session_state.cart:
        st.write(f"🔹 {item['id']} — {item['name']}")

    # =========================
    # PROCESS CHECKOUT
    # =========================
    if st.button("Process Checkout"):

        if not st.session_state.employee:

            st.error("Employee required")
            st.stop()

        if len(st.session_state.cart) == 0:

            st.error("No assets scanned")
            st.stop()

        for item in st.session_state.cart:
            asset = item["id"]

            row_index, item = find_row(asset)

            if row_index:

                inventory_sheet.update_cell(
                    row_index,
                    9,
                    "Checked Out"
                )

                inventory_sheet.update_cell(
                    row_index,
                    11,
                    st.session_state.employee
                )

                add_history(
                    "Checkout",
                    asset,
                    st.session_state.employee
                )

        st.success("✅ Checkout completed")

        st.session_state.cart = []
        st.session_state.last_scanned = ""

    if st.button("Done"):

        reset_session()
        st.rerun()

# =========================
# CHECKIN
# =========================
elif st.session_state.mode == "checkin":

    st.title("📥 Checkin Mode")

    st.subheader("📷 Scan Asset")

    qr_value = qrcode_scanner()

    if (
        qr_value and
        qr_value != st.session_state.last_scanned
    ):

        st.session_state.last_scanned = qr_value

        row_index, item = find_row(qr_value)

        if not item:

            st.error(f"{qr_value} not found")

        else:

            inventory_sheet.update_cell(
                row_index,
                9,
                "Available"
            )

            inventory_sheet.update_cell(
                row_index,
                11,
                ""
            )

            add_history(
                "Checkin",
                qr_value
            )

            st.success(f"✅ Checked in {qr_value}")

    if st.button("Done"):

        reset_session()
        st.rerun()