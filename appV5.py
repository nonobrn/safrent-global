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
BASE_URL = "https://safrent-global-ofimvwejhndxmemgwjjtfr.streamlit.app" 

# --- SIMULATION DES CLÉS (Pour la démo) ---
# Dans la réalité, la Private Key est secrète et stockée uniquement chez le validateur.
# Ici, on génère une paire fixe pour que la démo fonctionne tout de suite.
DEMO_PRIVATE_KEY_HEX = "e6e3428b80980c65796695245862309101037380120197022205517112265087"
try:
    VALIDATOR_SK = SigningKey.from_string(bytes.fromhex(DEMO_PRIVATE_KEY_HEX), curve=SECP256k1)
    VALIDATOR_VK = VALIDATOR_SK.verifying_key
    VALIDATOR_PUB_KEY_HEX = VALIDATOR_VK.to_string().hex()
except:
    # Fallback si ecdsa n'est pas installé ou erreur
    VALIDATOR_PUB_KEY_HEX = "demo-key"

TRUSTED_VALIDATORS = {
    "NEOMA BS": VALIDATOR_PUB_KEY_HEX
}

# ==========================================
# 🔐 BLOCKCHAIN LOGIC (WITH SIGNATURES)
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
        """Vérifie mathématiquement que le message vient bien du possesseur de la clé privée."""
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(pub_key_hex), curve=SECP256k1)
            return vk.verify(bytes.fromhex(signature_hex), message.encode())
        except:
            return False

    def add_signed_block(self, request_data, signature, validator_name):
        """Ajoute un bloc SEULEMENT si la signature est valide."""
        previous_block = self.get_last_block()
        prev_hash = previous_block.get("hash", "0") if previous_block else "0"
        
        timestamp = datetime.now().isoformat()
        student_id = request_data['student_id']
        details = request_data['details']
        score = request_data['score']

        # 1. Reconstruction du message qui a été signé
        # Le validateur signe : student_id + details + score
        message_to_verify = f"{student_id}{details}{score}"
        
        # 2. Vérification de la signature
        pub_key = TRUSTED_VALIDATORS.get(validator_name)
        if not pub_key:
            return False, "Validator not found in trusted list."

        if not self.verify_signature(message_to_verify, signature, pub_key):
            return False, "Invalid Cryptographic Signature!"

        # 3. Création du bloc Blockchain (avec hachage chaîné)
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
        return True, "Block successfully mined and added."

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
# 🚦 SESSION & ROUTING
# ==========================================
if "student_id" not in st.session_state:
    st.session_state["student_id"] = str(uuid.uuid4())[:8]

# Gestion des demandes en attente (Mémoire temporaire)
if "pending_requests" not in st.session_state:
    st.session_state["pending_requests"] = []

query_params = st.query_params
verify_id = query_params.get("verify_id", None)

# ==========================================
# 🕵️‍♂️ MODE VALIDATEUR (SIDEBAR)
# ==========================================
st.sidebar.header("🔐 Node Access")
is_validator = st.sidebar.checkbox("I am a Validator")

if is_validator:
    password = st.sidebar.text_input("Node Key / Password", type="password")
    
    # ⚠️ ATTENTION AUX ESPACES ICI (4 espaces après le 'if', 8 espaces après le 2ème 'if')
    if password == "nono401": 
        st.sidebar.success("Node: NEOMA BS (Connected)")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Pending Approvals")
        
        if len(st.session_state["pending_requests"]) > 0:
            req = st.session_state["pending_requests"][0] # Prend la première demande
            st.sidebar.info(f"Student: {req['student_id']}\nScore: {req['score']}")
            
            if st.sidebar.button("✅ Sign & Approve"):
                # 1. Signature cryptographique
                msg = f"{req['student_id']}{req['details']}{req['score']}"
                signature = VALIDATOR_SK.sign(msg.encode()).hex()
                
                # 2. Envoi au Ledger
                success, msg = ledger_system.add_signed_block(req, signature, "NEOMA BS")
                
                if success:
                    st.session_state["pending_requests"].pop(0)
                    st.sidebar.success("Block signed & mined!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.sidebar.error(f"Error: {msg}")
        else:
            st.sidebar.write("No pending requests.")
    elif password:
        st.sidebar.error("Invalid Access Key")

# ==========================================
# 👔 LANDLORD VIEW
# ==========================================
if verify_id:
    st.title("🛡️ Verification Portal")
    record = ledger_system.get_student_score(verify_id)
    
    if record:
        score = record.get('score', 0)
        st.metric("Certified RentScore", f"{score}/100")
        st.info(f"Student ID: {verify_id}")
        
        st.success(f"✅ Verified by Node: **{record.get('validator', 'Unknown')}**")
        
        with st.expander("See Cryptographic Proof"):
            st.text(f"Signature:\n{record.get('signature')}")
            st.text(f"Block Hash:\n{record.get('hash')}")
            
    else:
        st.error("Student ID not found in Blockchain.")
    
    if st.button("Home"):
        st.query_params.clear()
        st.rerun()
    st.stop()

# ==========================================
# 🎓 STUDENT DASHBOARD
# ==========================================
st.title("🌍 SafeRent Global")
st.caption(f"Student ID: {st.session_state['student_id']}")

tabs = st.tabs(["📝 Request Validation", "📊 My QR Code", "⛓️ Ledger Explorer"])

with tabs[0]:
    st.header("Update Profile")
    st.info("ℹ️ Updates must be validated by a trusted Node before appearing on the blockchain.")
    
    col1, col2, col3 = st.columns(3)
    income = col1.slider("Income", 0, 100, 50)
    guarantor = col2.slider("Guarantor", 0, 100, 50)
    history = col3.slider("History", 0, 100, 50)

    current_score = calculate_rent_score(income, guarantor, history)
    st.metric("Projected Score", current_score)
    
    if st.button("📩 Send to University for Validation"):
        req = {
            "student_id": st.session_state['student_id'],
            "details": f"{income}-{guarantor}-{history}",
            "score": current_score,
            "timestamp": time.time()
        }
        st.session_state["pending_requests"].append(req)
        st.success("Request sent to the Validator Node! Please ask an admin to approve it.")

with tabs[1]:
    last_record = ledger_system.get_student_score(st.session_state['student_id'])
    if last_record:
        url = f"{BASE_URL}/?verify_id={st.session_state['student_id']}"
        st.image(generate_custom_qr(url), width=200)
        st.success("Your score is active and verified.")
    else:
        st.warning("No verified score yet. Please request validation first.")

with tabs[2]:
    st.write(ledger_system.chain)
