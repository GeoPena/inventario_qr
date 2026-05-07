import streamlit as st
import gspread
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
defaults = {
    "mode": "home",
    "employee": "",
    "cart": [],
    "qr_input": "",
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
# QR SCANNER
# =========================
def qr_scanner():

    scanner_html = """
    <script src="https://unpkg.com/html5-qrcode"></script>

    <div id="reader" style="width:100%;"></div>

    <button id="start-btn"
        style="
            padding:12px;
            border-radius:10px;
            border:none;
            background:#ff4b4b;
            color:white;
            font-size:16px;
            width:100%;
            margin-top:10px;
        ">
        Start Scanner
    </button>

    <script>

    let scanner;

    async function startScanner() {

        scanner = new Html5Qrcode("reader");

        const devices = await Html5Qrcode.getCameras();

        let cameraId = devices[0].id;

        devices.forEach(device => {

            const label = device.label.toLowerCase();

            if (
                label.includes("back") ||
                label.includes("rear") ||
                label.includes("environment")
            ) {
                cameraId = device.id;
            }

        });

        scanner.start(
            cameraId,
            {
                fps: 10,
                qrbox: 250
            },
            (decodedText) => {

                const qrInput =
                    window.parent.document.querySelector(
                        'input[aria-label="QR_HIDDEN_INPUT"]'
                    );

                if (qrInput) {

                    qrInput.value = decodedText;

                    qrInput.dispatchEvent(
                        new Event("input", { bubbles: true })
                    );

                }

            }
        );

    }

    document
        .getElementById("start-btn")
        .addEventListener("click", startScanner);

    </script>
    """

    components.html(scanner_html, height=500)

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

    # hidden input
    st.text_input(
        "QR_HIDDEN_INPUT",
        key="qr_input",
        label_visibility="collapsed"
    )

    st.subheader("📷 QR Scanner")

    qr_scanner()

    # =========================
    # PROCESS QR
    # =========================
    qr_value = st.session_state.qr_input.strip()

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

                st.session_state.cart.append(qr_value)

                st.success(f"✅ Added {qr_value}")

    # =========================
    # CURRENT SESSION
    # =========================
    st.subheader("📦 Current Session")

    st.write(st.session_state.cart)

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

        for asset in st.session_state.cart:

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
        st.session_state.qr_input = ""
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
        "QR_HIDDEN_INPUT",
        key="qr_input",
        label_visibility="collapsed"
    )

    st.subheader("📷 QR Scanner")

    qr_scanner()

    qr_value = st.session_state.qr_input.strip()

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