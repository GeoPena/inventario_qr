import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# =========================
# GOOGLE SHEETS
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

if "last_message" not in st.session_state:
    st.session_state.last_message = ""

# =========================
# HELPERS
# =========================
def reset_session():
    st.session_state.employee = ""
    st.session_state.cart = []
    st.session_state.last_message = ""
    st.session_state.mode = "home"

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
# HOME SCREEN
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

    employee = st.text_input(
        "Employee Name",
        value=st.session_state.employee
    )

    st.session_state.employee = employee

    def add_asset():

        asset = st.session_state.asset_input.strip()

        if not asset:
            return

        row_index, item = find_row(asset)

        if not item:
            st.session_state.last_message = f"❌ {asset} not found"
            return

        status = item["Status"]

        if status != "Available":
            st.session_state.last_message = f"⚠ {asset} is {status}"
            return

        if asset not in st.session_state.cart:
            st.session_state.cart.append(asset)
            st.session_state.last_message = f"✅ Added {asset}"

        st.session_state.asset_input = ""

    st.text_input(
        "Scan AssetID",
        key="asset_input",
        on_change=add_asset
    )

    st.write(st.session_state.last_message)

    st.subheader("📦 Current Session")
    st.write(st.session_state.cart)

    if st.button("Process Checkout"):

        if not st.session_state.employee:
            st.error("Employee required")
            st.stop()

        if len(st.session_state.cart) == 0:
            st.error("No assets scanned")
            st.stop()

        for asset in st.session_state.cart:

            row_index, item = find_row(asset)

            if row_index:

                inventory_sheet.update_cell(row_index, 9, "Checked Out")
                inventory_sheet.update_cell(row_index, 11, st.session_state.employee)

                add_history(
                    "Checkout",
                    asset,
                    st.session_state.employee
                )

        st.success("✅ Checkout completed")

    if st.button("Done"):
        reset_session()
        st.rerun()

# =========================
# CHECKIN MODE
# =========================
elif st.session_state.mode == "checkin":

    st.title("📥 Checkin Mode")

    notes = st.text_input("Optional Notes")

    def process_checkin():

        asset = st.session_state.checkin_asset.strip()

        if not asset:
            return

        row_index, item = find_row(asset)

        if not item:
            st.session_state.last_message = f"❌ {asset} not found"
            return

        inventory_sheet.update_cell(row_index, 9, "Available")
        inventory_sheet.update_cell(row_index, 11, "")

        add_history(
            "Checkin",
            asset,
            "",
            notes
        )

        st.session_state.last_message = f"✅ Checked in {asset}"
        st.session_state.checkin_asset = ""

    st.text_input(
        "Scan AssetID",
        key="checkin_asset",
        on_change=process_checkin
    )

    st.write(st.session_state.last_message)

    if st.button("Done"):
        reset_session()
        st.rerun()