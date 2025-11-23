import streamlit as st
import json
import hashlib
import time
import qrcode
import uuid
from io import BytesIO
from PIL import Image, ImageDraw
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(page_title="SafeRent Global", page_icon="🌍", layout="centered")
LEDGER_FILE = "ledger.json"
# ⚠️ Update this URL to your actual Streamlit deployment URL
BASE_URL = "https://safrent-global-ofimvwejhndxmemgwjjtfr.streamlit.app"

# --- KEY SIMULATION (For Demo Purposes) ---
DEMO_PRIVATE_KEY_HEX = "e6e3428b80980c65796695245862309101037380120197022205517112265087"
try:
    VALIDATOR_SK = SigningKey.from_string(bytes.fromhex(DEMO_PRIVATE_KEY_HEX), curve=SECP256k1)
    VALIDATOR_VK = VALIDATOR_SK.verifying_key
    VALIDATOR_PUB_KEY_HEX = VALIDATOR_VK.to_string().hex()
except:
    VALIDATOR_PUB_KEY_HEX = "demo-key"

TRUSTED_VALIDATORS = {
    "NEOMA BS": VALIDATOR_PUB_KEY_HEX
}

# ==========================================
# 🔐 BLOCKCHAIN LOGIC
# ==========================================
class LedgerSystem:
    def __init__(self):
        self.filename = LEDGER_FILE
        self.chain = self.load_chain()

    def load_chain(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_chain(self):
        with open(self.filename, "w") as f:
            json.dump(self.chain, f, indent=4)

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def verify_signature(self, message, signature_hex, pub_key_hex):
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(pub_key_hex), curve=SECP256k1)
            return vk.verify(bytes.fromhex(signature_hex), message.encode())
        except:
            return False

    def add_signed_block(self, request_data, signature, validator_name):
        previous_block = self.get_last_block()
        prev_hash = previous_block.get("hash", "0") if previous_block else "0"
        
        timestamp = datetime.now().isoformat()
        student_id = request_data['student_id']
        details = request_data['details']
        score = request_data['score']

        message_to_verify = f"{student_id}{details}{score}"
        
        pub_key = TRUSTED_VALIDATORS.get(validator_name)
        if not pub_key:
            return False, "Validator not found."

        if not self.verify_signature(message_to_verify, signature, pub_key):
            return False, "Invalid Signature!"

        block_content = f"{student_id}{details}{timestamp}{prev_hash}{signature}"
        new_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        block = {
            "index": len(self.chain) + 1,
            "timestamp": timestamp,
            "student_id": student_id,
            "details": details,
            "score": score,
            "validator": validator_name,
            "signature": signature,
            "previous_hash": prev_hash,
            "hash": new_hash
        }
        
        self.chain.append(block)
        self.save_chain()
        return True, "Block mined."

    def get_student_score(self, student_id):
        for block in reversed(self.chain): 
            if block.get("student_id") == student_id:
                return block
        return None

    def verify_chain_integrity(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current.get("previous_hash") != previous.get("hash"):
                return False
        return True

ledger_system = LedgerSystem()

# ==========================================
# 🧮 HELPERS
# ==========================================
def calculate_rent_score(income, guarantor, history):
    return min(int(income * 0.4 + guarantor * 0.3 + history * 0.2 + 10), 100)

def generate_custom_qr(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    border_color = (66, 135, 245)
    img_w, img_h = img.size
    background = Image.new('RGB', (img_w + 20, img_h + 20), border_color)
    background.paste(img, (10, 10))
    buffer = BytesIO()
    background.save(buffer, format="PNG")
    return buffer.getvalue()

# ==========================================
# 🚦 STATE & ROUTING
# ==========================================
if "student_id" not in st.session_state:
    st.session_state["student_id"] = str(uuid.uuid4())[:8]

if "pending_requests" not in st.session_state:
    st.session_state["pending_requests"] = []

# Navigation state: 'home', 'validator_dashboard'
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "home"

query_params = st.query_params
verify_id = query_params.get("verify_id", None)

# ==========================================
# 🛡️ VIEW 1: LANDLORD PORTAL (Public)
# ==========================================
if verify_id:
    st.title("🛡️ Verification Portal")
    st.markdown("---")
    
    record = ledger_system.get_student_score(verify_id)
    
    if record:
        score = record.get('score', 0)
        
        # --- COLORED BANNERS ---
        if score >= 80:
            st.success(f"🌟 EXCELLENT PROFILE ({score}/100)\n\nHighly recommended candidate. Strong guarantees.")
        elif score >= 50:
            st.warning(f"⚠️ AVERAGE PROFILE ({score}/100)\n\nStandard candidate. Usual checks recommended.")
        else:
            st.error(f"🛑 RISKY PROFILE ({score}/100)\n\nInsufficient guarantees. Caution advised.")
        # -----------------------

        col1, col2 = st.columns([1, 2])
        with col1:
             st.metric("Certified RentScore", f"{score}/100")
        with col2:
            st.info(f"👤 Student ID: **{verify_id}**\n\n🏫 Verified by: **{record.get('validator', 'Unknown')}**")
        
        with st.expander("View Cryptographic Proof"):
            st.code(f"Signature: {record.get('signature')}\nHash: {record.get('hash')}")
            
    else:
        st.error("❌ This record was not found in the Blockchain.")
    
    if st.button("🏠 Return to Home"):
        st.query_params.clear()
        st.rerun()
    
    st.stop() # Stops script execution here for the landlord

# ==========================================
# 🔐 VIEW 2: VALIDATOR DASHBOARD (Restricted)
# ==========================================
if st.session_state["current_view"] == "validator_dashboard":
    st.title("🔐 Validator Dashboard (NEOMA BS)")
    
    # Navbar
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("⬅️ Home"):
            st.session_state["current_view"] = "home"
            st.rerun()
    with col_nav2:
        if st.button("🔄 Refresh List"):
            st.rerun()
            
    st.markdown("---")
    st.subheader("📋 Pending Requests")
    
    if len(st.session_state["pending_requests"]) > 0:
        # Display requests as cards
        for i, req in enumerate(st.session_state["pending_requests"]):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**Student:** `{req['student_id']}`")
                c1.text(f"Details: {req['details']}")
                c2.metric("Score", req['score'])
                
                if c3.button("✅ Sign & Validate", key=f"btn_{i}"):
                    # Signature
                    msg = f"{req['student_id']}{req['details']}{req['score']}"
                    signature = VALIDATOR_SK.sign(msg.encode()).hex()
                    
                    # Send to Blockchain
                    success, msg = ledger_system.add_signed_block(req, signature, "NEOMA BS")
                    
                    if success:
                        st.session_state["pending_requests"].pop(i)
                        st.success("Block validated and added to the blockchain!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
    else:
        st.info("No pending requests at the moment.")
        
    st.stop() # Stops script execution here for the validator

# ==========================================
# 🎓 VIEW 3: STUDENT HOME (Default)
# ==========================================
st.title("🌍 SafeRent Global")
st.caption(f"Your Student ID: {st.session_state['student_id']}")

# --- Sidebar Login to switch to Validator Mode ---
st.sidebar.header("Staff / Validator Access")
password = st.sidebar.text_input("Access Key", type="password")
if st.sidebar.button("Login"):
    if password == "nono401":
        st.session_state["current_view"] = "validator_dashboard"
        st.rerun()
    else:
        st.sidebar.error("Incorrect password")
# -------------------------------------------------

tabs = st.tabs(["📝 Request Validation", "📊 My QR Code", "⛓️ Ledger Explorer"])

with tabs[0]:
    st.write("### Update Profile")
    st.info("ℹ️ Your data must be validated by NEOMA BS before appearing on your QR Code.")
    
    col1, col2, col3 = st.columns(3)
    income = col1.slider("Income (0-100)", 0, 100, 50)
    guarantor = col2.slider("Guarantor (0-100)", 0, 100, 50)
    history = col3.slider("History (0-100)", 0, 100, 50)

    current_score = calculate_rent_score(income, guarantor, history)
    st.metric("Projected Score", current_score)
    
    if st.button("📩 Send for Validation"):
        req = {
            "student_id": st.session_state['student_id'],
            "details": f"{income}-{guarantor}-{history}",
            "score": current_score,
            "timestamp": time.time()
        }
        st.session_state["pending_requests"].append(req)
        st.success("Request sent! Waiting for validator signature.")

with tabs[1]:
    last_record = ledger_system.get_student_score(st.session_state['student_id'])
    if last_record:
        url = f"{BASE_URL}/?verify_id={st.session_state['student_id']}"
        st.image(generate_custom_qr(url), width=200)
        st.success("Your profile is certified and active.")
        st.write("Show this QR code to your future landlord.")
    else:
        st.warning("No certified score yet. Please submit a request in the first tab.")

with tabs[2]:
    st.subheader("Blockchain Transparency")
    st.write(ledger_system.chain)
