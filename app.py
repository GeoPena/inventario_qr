import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_qrcode_scanner import qrcode_scanner

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Marbella Asset Management",
    layout="centered"
)

# =========================
# BRAND HEADER (LOGO)
# =========================
col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.image("logo.png", width=260)

st.markdown("<br>", unsafe_allow_html=True)

# =========================
# CUSTOM STYLES (MARBELLA LOOK)
# =========================
st.markdown("""
<style>

/* BACKGROUND */
.stApp {
    background-color: #F4F8FF;
}

/* TITLES */
h1, h2, h3 {
    color: #0449A4 !important;
    font-weight: 700;
}

/* BUTTONS */
.stButton button {
    background-color: #F47C20;
    color: white;
    border-radius: 12px;
    height: 3em;
    font-weight: 600;
    border: none;
    transition: 0.2s;
}

.stButton button:hover {
    transform: scale(1.02);
    background-color: #e86f15;
}

/* INPUTS */
.stTextInput input {
    border-radius: 10px;
    border: 1px solid #d0d7e2;
}

/* CARDS */
div[data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}

</style>
""", unsafe_allow_html=True)

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
    "checkin_notes": "",
    "manual_checkout": "",
    "manual_checkin": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# HELPERS
# =========================
def reset_session():
    st.session_state.update({
        "mode": "home",
        "employee": "",
        "cart": [],
        "last_scanned": "",
        "checkin_notes": "",
        "manual_checkout": "",
        "manual_checkin": ""
    })


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
    st.rerun()


# =========================
# PROCESS SCAN
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

        if not any(c["id"] == value for c in st.session_state.cart):

            st.session_state.cart.append({
                "id": value,
                "name": item_name
            })

            st.success(f"Added {item_name}")

    # =========================
    # CHECKIN
    # =========================
    elif st.session_state.mode == "checkin":

        if not row:
            st.error(f"{value} not found")
            return

        inventory_sheet.update_cell(row_index, 9, "Available")
        inventory_sheet.update_cell(row_index, 11, "")

        add_history(
            "Checkin",
            value,
            "",
            st.session_state.checkin_notes
        )

        st.success(f"Checked in {value}")

        st.session_state.checkin_notes = ""


# =========================
# HOME
# =========================
if st.session_state.mode == "home":

    st.title("Asset Management System")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📤 CHECKOUT", use_container_width=True):
            st.session_state.mode = "checkout"
            st.rerun()

    with col2:
        if st.button("📥 CHECKIN", use_container_width=True):
            st.session_state.mode = "checkin"
            st.rerun()


# =========================
# CHECKOUT
# =========================
elif st.session_state.mode == "checkout":

    st.title("📤 Checkout")

    st.text_input("Employee Name", key="employee")

    st.subheader("Scan Asset")

    qr_value = qrcode_scanner()
    process_scan(qr_value)

    manual_value = st.text_input("Manual Asset ID", key="manual_checkout")
    if manual_value:
        process_scan(manual_value)

    st.subheader("Current Cart")

    for item in st.session_state.cart:
        col1, col2 = st.columns([5,1])
        with col1:
            st.write(f"{item['name']} ({item['id']})")
        with col2:
            st.button("❌", key=item["id"], on_click=remove_from_cart, args=(item["id"],))

    if st.button("Process Checkout", use_container_width=True):

        if not st.session_state.employee:
            st.error("Employee required")
            st.stop()

        for item in st.session_state.cart:

            row_index, _ = find_row(item["id"])

            if row_index:
                inventory_sheet.update_cell(row_index, 9, "Checked Out")
                inventory_sheet.update_cell(row_index, 11, st.session_state.employee)

                add_history("Checkout", item["id"], st.session_state.employee)

        st.success("Checkout completed")
        reset_session()
        st.rerun()


    if st.button("Done", use_container_width=True):
        reset_session()
        st.rerun()


# =========================
# CHECKIN
# =========================
elif st.session_state.mode == "checkin":

    st.title("📥 Checkin")

    st.text_input(
        "Notes (optional)",
        key="checkin_notes",
        placeholder="Damage, issues, etc..."
    )

    st.subheader("Scan Asset")

    qr_value = qrcode_scanner()
    process_scan(qr_value)

    manual_value = st.text_input("Manual Asset ID", key="manual_checkin")
    if manual_value:
        process_scan(manual_value)

    if st.button("Done", use_container_width=True):
        reset_session()
        st.rerun()