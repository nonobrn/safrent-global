import streamlit as st
import json
import hashlib
import time
import qrcode
import uuid
import os
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(page_title="SafeRent Global", page_icon="🌍", layout="centered")
LEDGER_FILE = "ledger.json"
PENDING_FILE = "pending.json"
REJECTED_FILE = "rejected.json"
ACCEPTED_FILE = "accepted.json"

# ⚠️ Update this URL to your actual Streamlit deployment URL
BASE_URL = "https://safrent-global-4o6mscpnwgpvpgvxucynne.streamlit.app"

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
# 📂 PERSISTENCE MANAGER (HANDLES FILES)
# ==========================================
class DataManager:
    """Handles reading/writing JSON files to allow communication between users."""
    
    @staticmethod
    def load_json(filename):
        if not os.path.exists(filename):
            return []
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except:
            return []

    @staticmethod
    def save_json(filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def add_pending_request(request):
        data = DataManager.load_json(PENDING_FILE)
        data.append(request)
        DataManager.save_json(PENDING_FILE, data)

    @staticmethod
    def get_pending_requests():
        return DataManager.load_json(PENDING_FILE)

    @staticmethod
    def remove_pending_request(request_timestamp):
        data = DataManager.load_json(PENDING_FILE)
        new_data = [req for req in data if req.get("timestamp") != request_timestamp]
        DataManager.save_json(PENDING_FILE, new_data)

    # --- REJECTION LOGIC ---
    @staticmethod
    def add_rejection(student_id, reason):
        data = DataManager.load_json(REJECTED_FILE)
        data.append({
            "student_id": student_id,
            "reason": reason,
            "timestamp": time.time()
        })
        DataManager.save_json(REJECTED_FILE, data)

    @staticmethod
    def get_rejection(student_id):
        data = DataManager.load_json(REJECTED_FILE)
        for item in reversed(data):
            if item["student_id"] == student_id:
                return item
        return None

    @staticmethod
    def clear_rejection(student_id):
        data = DataManager.load_json(REJECTED_FILE)
        new_data = [item for item in data if item["student_id"] != student_id]
        DataManager.save_json(REJECTED_FILE, new_data)

    # --- ACCEPTANCE LOGIC ---
    @staticmethod
    def add_acceptance(student_id):
        data = DataManager.load_json(ACCEPTED_FILE)
        data.append({
            "student_id": student_id,
            "timestamp": time.time()
        })
        DataManager.save_json(ACCEPTED_FILE, data)

    @staticmethod
    def get_acceptance(student_id):
        data = DataManager.load_json(ACCEPTED_FILE)
        for item in reversed(data):
            if item["student_id"] == student_id:
                return item
        return None

    @staticmethod
    def clear_acceptance(student_id):
        data = DataManager.load_json(ACCEPTED_FILE)
        new_data = [item for item in data if item["student_id"] != student_id]
        DataManager.save_json(ACCEPTED_FILE, new_data)


# ==========================================
# 🔐 BLOCKCHAIN LOGIC
# ==========================================
class LedgerSystem:
    def __init__(self):
        self.filename = LEDGER_FILE
        self.chain = self.load_chain()

    def load_chain(self):
        return DataManager.load_json(self.filename)

    def save_chain(self):
        DataManager.save_json(self.filename, self.chain)

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def verify_signature(self, message, signature_hex, pub_key_hex):
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(pub_key_hex), curve=SECP256k1)
            return vk.verify(bytes.fromhex(signature_hex), message.encode())
        except:
            return False

    def add_signed_block(self, request_data, signature, validator_name):
        self.chain = self.load_chain()
        
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
        self.chain = self.load_chain()
        target_id = str(student_id).strip()
        for block in reversed(self.chain):
            block_id = str(block.get("student_id", "")).strip()
            if block_id == target_id:
                return block
        return None

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

def create_digital_certificate(qr_bytes, student_id, block_hash, signature):
    """Creates a certificate image with QR + Hash + Signature."""
    # Load QR
    qr_img = Image.open(BytesIO(qr_bytes))
    
    # Canvas setup
    width = 600
    height = 950
    bg_color = "white"
    cert = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(cert)
    
    # Paste QR in center top
    qr_w, qr_h = qr_img.size
    offset_x = (width - qr_w) // 2
    cert.paste(qr_img, (offset_x, 50))
    
    # Header
    draw.text((20, qr_h + 70), f"SafeRent Digital Certificate", fill="blue")
    draw.text((20, qr_h + 90), f"Student ID: {student_id}", fill="black")
    
    # Formatting long text
    margin = 20
    current_h = qr_h + 130
    
    # Hash
    draw.text((margin, current_h), "Blockchain Hash:", fill="red")
    current_h += 20
    wrapped_hash = textwrap.wrap(block_hash, width=60)
    for line in wrapped_hash:
        draw.text((margin, current_h), line, fill="black")
        current_h += 15
        
    current_h += 30
    
    # Signature
    draw.text((margin, current_h), "Validator Signature (NEOMA BS):", fill="green")
    current_h += 20
    wrapped_sig = textwrap.wrap(signature, width=60)
    for line in wrapped_sig:
        draw.text((margin, current_h), line, fill="black")
        current_h += 15
        
    draw.text((margin, current_h + 40), f"Generated: {datetime.now().strftime('%Y-%m-%d')}", fill="gray")

    return cert

# ==========================================
# 🚦 STATE & ROUTING
# ==========================================
if "student_id" not in st.session_state:
    st.session_state["student_id"] = str(uuid.uuid4())[:8]

if "pending_requests" not in st.session_state:
    st.session_state["pending_requests"] = []

if "current_view" not in st.session_state:
    st.session_state["current_view"] = "home"

query_params = st.query_params
verify_id = query_params.get("verify_id", None)

# ==========================================
# 🛡️ VIEW 1: LANDLORD PORTAL (Public)
# ==========================================
if verify_id:
    clean_verify_id = verify_id.strip()
    
    st.title("🛡️ Verification Portal")
    st.markdown("---")
    
    record = ledger_system.get_student_score(clean_verify_id)
    
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
            st.info(f"👤 Student ID: **{clean_verify_id}**\n\n🏫 Verified by: **{record.get('validator', 'Unknown')}**")
        
        with st.expander("View Cryptographic Proof"):
            st.code(f"Signature: {record.get('signature')}\nHash: {record.get('hash')}")
            
    else:
        st.error(f"❌ Record not found for ID: {clean_verify_id}")
        
        with st.expander("🔍 Debugging Help (Why is this failing?)"):
            st.write(f"👉 **We looked for:** '{clean_verify_id}'")
            st.write("👉 **Currently inside ledger.json:**")
            all_ids = [str(b.get("student_id")).strip() for b in ledger_system.chain]
            st.write(all_ids)
            if len(all_ids) == 0:
                st.warning("⚠️ The ledger is empty!")
            elif clean_verify_id in all_ids:
                st.success("✅ The ID exists! Try refreshing.")
            else:
                st.error("❌ The ID is missing.")
    
    st.markdown("---")
    
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    with col_act2:
        if st.button("🏠 Return to Home", use_container_width=True):
            st.query_params.clear()
            st.rerun()
    
    st.stop() 

# ==========================================
# 🔐 VIEW 2: VALIDATOR DASHBOARD (Restricted)
# ==========================================
if st.session_state["current_view"] == "validator_dashboard":
    st.title("🔐 Validator Dashboard (NEOMA BS)")
    
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
    
    pending_list = DataManager.get_pending_requests()

    if len(pending_list) > 0:
        for req in pending_list:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**Student:** `{req['student_id']}`")
                c1.text(f"Details: {req['details']}")
                c2.metric("Score", req['score'])
                
                col_accept, col_reject = c3.columns(2)
                
                if col_accept.button("✅ Accept", key=f"acc_{req['timestamp']}"):
                    msg = f"{req['student_id']}{req['details']}{req['score']}"
                    signature = VALIDATOR_SK.sign(msg.encode()).hex()
                    
                    success, msg = ledger_system.add_signed_block(req, signature, "NEOMA BS")
                    
                    if success:
                        DataManager.remove_pending_request(req['timestamp'])
                        DataManager.add_acceptance(req['student_id']) 
                        st.success("Validated!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

                if col_reject.button("❌ Reject", key=f"rej_{req['timestamp']}"):
                    DataManager.remove_pending_request(req['timestamp'])
                    DataManager.add_rejection(req['student_id'], "Data inconsistency detected by admin.")
                    st.warning("Rejected.")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("No pending requests at the moment.")
        
    st.stop() 

# ==========================================
# 🎓 VIEW 3: STUDENT HOME (Default)
# ==========================================
st.title("🌍 SafeRent Global")
st.caption(f"Your Student ID: {st.session_state['student_id']}")

if st.button("🔄 Refresh Status"):
    st.rerun()

# --- NOTIFICATIONS ---
acceptance = DataManager.get_acceptance(st.session_state['student_id'])
if acceptance:
    st.success("🎉 Great news! Your request has been successfully validated by NEOMA BS.")
    if st.button("Dismiss Success Message"):
        DataManager.clear_acceptance(st.session_state['student_id'])
        st.rerun()

rejection = DataManager.get_rejection(st.session_state['student_id'])
if rejection:
    st.error(f"❌ Your last request was rejected: {rejection['reason']}")
    if st.button("Dismiss Notification"):
        DataManager.clear_rejection(st.session_state['student_id'])
        st.rerun()

# --- SIDEBAR LOGIN ---
st.sidebar.header("Staff / Validator Access")
password = st.sidebar.text_input("Access Key", type="password")
if st.sidebar.button("Login"):
    if password == "nono401":
        st.session_state["current_view"] = "validator_dashboard"
        st.rerun()
    else:
        st.sidebar.error("Incorrect password")

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
        DataManager.add_pending_request(req)
        st.success("Request sent! Waiting for validator signature.")

with tabs[1]:
    last_record = ledger_system.get_student_score(st.session_state['student_id'])
    
    if last_record:
        url = f"{BASE_URL}/?verify_id={st.session_state['student_id']}"
        qr_bytes = generate_custom_qr(url)
        st.image(qr_bytes, width=200)
        st.success("Your profile is certified and active.")
        st.write("Show this QR code to your future landlord.")
        
        # --- CERTIFICATE GENERATION ---
        cert_img = create_digital_certificate(
            qr_bytes, 
            st.session_state['student_id'], 
            last_record.get('hash', 'N/A'),
            last_record.get('signature', 'N/A')
        )
        
        # Convert to PNG bytes
        png_buffer = BytesIO()
        cert_img.save(png_buffer, format="PNG")
        png_data = png_buffer.getvalue()
        
        # Convert to PDF bytes
        pdf_buffer = BytesIO()
        cert_img.save(pdf_buffer, format="PDF")
        pdf_data = pdf_buffer.getvalue()
        
        st.markdown("### 📥 Download Proof")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.download_button("🖼️ Download as PNG", png_data, file_name="SafeRent_Certificate.png", mime="image/png")
        with d_col2:
            st.download_button("📄 Download as PDF", pdf_data, file_name="SafeRent_Certificate.pdf", mime="application/pdf")
        # -----------------------------
        
        with st.expander("Show Raw Data Details"):
             st.json(last_record)
    else:
        st.warning("No certified score yet. Please submit a request in the first tab.")

with tabs[2]:
    st.subheader("Blockchain Transparency")
    st.write(ledger_system.chain)
