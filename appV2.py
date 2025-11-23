import streamlit as st
import json
import hashlib
import time
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw
from datetime import datetime

LEDGER_FILE = "ledger.json"

# ---------- Ledger helpers ----------
def load_ledger():
    try:
        with open(LEDGER_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_ledger(data):
    with open(LEDGER_FILE, "w") as f:
        json.dump(data, f, indent=4)
now = datetime.now()
formatted_timestamp = now.strftime("%d%m%Y : %H%M")  # DDMMAAA : HHMM

def add_entry(entry_type, details):
    ledger = load_ledger()
    entry = {
        "timestamp": formatted_timestamp,
        "type": entry_type,
        "details": details,
        "hash": hashlib.sha256(details.encode()).hexdigest()
    }
    ledger.append(entry)
    save_ledger(ledger)

# ---------- RentScore calculation ----------
def calculate_rent_score(income, guarantor, history):
    score = (
        income * 0.4 +
        guarantor * 0.3 +
        history * 0.2 +
        10   # Base score advantage for international students
    )
    return min(int(score), 100)

# ---------- QR generator ----------
def generate_qr(data):
    # Create basic QR
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Add a colored border around the QR
    border_color = (66, 135, 245)  # Light blue SafeRent theme
    bordered = Image.new("RGB", (img.size[0] + 40, img.size[1] + 40), border_color)
    bordered.paste(img, (20, 20))

    # Add a small circle "logo" in the center
    logo_size = 70
    logo = Image.new("RGB", (logo_size, logo_size), (255, 255, 255))
    draw = ImageDraw.Draw(logo)
    draw.ellipse((0, 0, logo_size, logo_size), fill="white", outline=border_color, width=4)

    # Add text inside the circle
    draw.text((logo_size//2 - 20, logo_size//2 - 10), "SG", fill=border_color)

    # Paste logo onto QR
    pos = ((bordered.size[0] - logo_size) // 2, (bordered.size[1] - logo_size) // 2)
    bordered.paste(logo, pos)

    # Convert to bytes
    buffer = BytesIO()
    bordered.save(buffer, format="PNG")
    return buffer.getvalue()

# ---------- Streamlit starts ----------
st.set_page_config(page_title="SafeRent Global", page_icon="🌍")

# Detect if the URL contains a score (landlord view)
query_params = st.query_params
incoming_score = query_params.get("score", None)

# ======================================================
# =============== LANDLORD VERIFICATION PAGE ===========
# ======================================================
if incoming_score:
    st.title("🏡 SafeRent Global — Verification Page")
    st.markdown("This page was opened by scanning a student's QR Code.")

    st.header("✔ Student RentScore")
    st.metric("RentScore", incoming_score)

    st.subheader("🔗 Ledger Summary")
    ledger = load_ledger()

    if ledger:
        st.json(ledger)
    else:
        st.info("No ledger entries available for this student.")

    st.success("This student's identity and data are verified through hashed ledger entries.")
    st.stop()

# ======================================================
# =============== STUDENT DASHBOARD PAGE =================
# ======================================================
st.title("🌍 SafeRent Global — Student Dashboard")
st.write("Build your international rental reputation and generate your QR Code.")

# Sidebar inputs
st.sidebar.header("Update your data")

income = st.sidebar.slider("Income (normalized 0–100)", 0, 100, 50)
guarantor = st.sidebar.slider("Guarantor Strength (0–100)", 0, 100, 50)
history = st.sidebar.slider("Rental History Score (0–100)", 0, 100, 50)

if st.sidebar.button("Update My Score"):
    add_entry("score_update", f"{income}-{guarantor}-{history}")
    st.sidebar.success("Score updated & added to ledger.")

# Compute RentScore
score = calculate_rent_score(income, guarantor, history)

st.header("🎯 Your RentScore")
st.metric("RentScore (0–100)", score)

# Ledger visualization
st.subheader("🧾 Ledger (Blockchain Simulation)")
ledger = load_ledger()
st.json(ledger)

# Generate QR Code pointing to the verification page
st.subheader("📲 Your Shareable QR Code")

# -------- IMPORTANT --------
# Replace this with your Streamlit Cloud URL once deployed:
BASE_URL = "https://safrent-global-s5q2bey6pnceo9t9vygnra.streamlit.app"
# Example for deployment:
# BASE_URL = "https://safrent-global.streamlit.app"

qr_url = f"{BASE_URL}/?score={score}"
qr_image = generate_qr(qr_url)

st.image(qr_image, caption="Your QR code is ready — show it to the landlord!")
st.write("Link encoded in QR:", qr_url)

st.download_button("Download QR Code", qr_image, "safrent_qr.png")

st.success("Your verification QR code is ready to share with landlords.")
