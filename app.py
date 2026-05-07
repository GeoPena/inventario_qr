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

inventory_sheet = client.open_by_url(SPREADSHEET_URL).worksheet("Inventory")
history_sheet = client.open_by_url(SPREADSHEET_URL).worksheet("History")

# =========================
# SESSION STATE
# =========================
defaults = {
    "mode": "home",
    "employee": "",
    "cart": [],
    "last_scanned": "",
    "checkin_notes": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# HELPERS
# =========================
def reset_session():

    st.session_state.mode = "home"
    st.session_state.employee = ""
    st.session_state.cart = []
    st.session_state.last_scanned = ""
    st.session_state.checkin_notes = ""


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


def remove_from_cart(asset_id):

    st.session_state.cart = [
        item for item in st.session_state.cart
        if item["id"] != asset_id
    ]

    st.session_state.last_scanned = ""


# =========================
# PROCESS SCAN (QR + MANUAL)
# =========================
def process_scan(value):

    if not value:
        return

    value = value.strip()

    if value == st.session_state.last_scanned:
        return

    st.session_state.last_scanned = value

    row_index, row = find_row(value)

    # =========================
    # CHECKOUT
    # =========================
    if st.session_state.mode == "checkout":

        if not row:
            st.error(f"{value} not found")
            return

        if row["Status"] != "Available":
            st.warning(f"{value} is {row['Status']}")
            return

        item_name = row.get("Name", "Unknown")

        for c in st.session_state.cart:
            if c["id"] == value:
                return

        st.session_state.cart.append({
            "id": value,
            "name": item_name
        })

        st.success(f"✅ Added {value} — {item_name}")

    # =========================
    # CHECKIN
    # =========================
    elif st.session_state.mode == "checkin":

        if not row:
            st.error(f"{value} not found")
            return

        notes = st.session_state.checkin_notes

        inventory_sheet.update_cell(row_index, 9, "Available")
        inventory_sheet.update_cell(row_index, 11, "")

        add_history(
            "Checkin",
            value,
            "",
            notes
        )

        st.success(f"✅ Checked in {value}")

        st.session_state.checkin_notes = ""


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

    st.text_input("Employee Name", key="employee")

    st.subheader("📷 Scan Asset")

    qr_value = qrcode_scanner()

    # QR input
    process_scan(qr_value)

    # MANUAL INPUT (fallback)
    manual_value = st.text_input("Or enter Asset ID manually")

    if manual_value:
        process_scan(manual_value)
        st.session_state["manual_checkout"] = ""


    # =========================
    # CART UI
    # =========================
    st.subheader("📦 Current Session")

    if len(st.session_state.cart) == 0:
        st.info("No items scanned yet")

    for item in st.session_state.cart:

        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(f"🔹 {item['id']} — {item['name']}")

        with col2:
            if st.button("❌", key=f"remove_{item['id']}"):
                remove_from_cart(item["id"])
                st.rerun()

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
            row_index, row = find_row(asset)

            if row_index:

                inventory_sheet.update_cell(row_index, 9, "Checked Out")
                inventory_sheet.update_cell(row_index, 11, st.session_state.employee)

                add_history("Checkout", asset, st.session_state.employee)

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

    st.text_input(
        "Notes (optional)",
        key="checkin_notes",
        placeholder="Write any issue or comment..."
    )

    st.subheader("📷 Scan Asset")

    qr_value = qrcode_scanner()

    process_scan(qr_value)

    # MANUAL INPUT (fallback)
    manual_value = st.text_input("Or enter Asset ID manually")

    if manual_value:
        process_scan(manual_value)
        st.session_state["manual_checkin"] = ""


    if st.button("Done"):
        reset_session()
        st.rerun()