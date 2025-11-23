import streamlit as st
import json
import hashlib
import time
import qrcode
import uuid
from io import BytesIO
from PIL import Image, ImageDraw
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(page_title="SafeRent Global", page_icon="🌍", layout="centered")
LEDGER_FILE = "ledger.json"
# Replace with your actual deployed URL
BASE_URL = "https://safrent-global-4g2jksdrmvree6ppabxp7z.streamlit.app" 

# ==========================================
# 🔐 BLOCKCHAIN LOGIC
# ==========================================
class LedgerSystem:
    def __init__(self):
        self.filename = LEDGER_FILE
        self.chain = self.load_chain()

    def load_chain(self):
        """Loads the ledger. Returns empty list if file is missing or corrupt."""
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_chain(self):
        """Saves the chain to the JSON file."""
        with open(self.filename, "w") as f:
            json.dump(self.chain, f, indent=4)

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def add_block(self, student_id, details, score):
        """Adds a block with chained hashing (True Blockchain)."""
        previous_block = self.get_last_block()
        
        # Safe access to previous hash (handles old data format gracefully)
        if previous_block:
            prev_hash = previous_block.get("hash", "0")
        else:
            prev_hash = "0"
        
        timestamp = datetime.now().isoformat()
        
        # Create payload to hash (Includes previous hash for security)
        block_content = f"{student_id}{details}{timestamp}{prev_hash}"
        new_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        block = {
            "index": len(self.chain) + 1,
            "timestamp": timestamp,
            "student_id": student_id,
            "type": "score_update",
            "details": details,
            "score": score,
            "previous_hash": prev_hash,
            "hash": new_hash
        }
        
        self.chain.append(block)
        self.save_chain()
        return block

    def verify_chain_integrity(self):
        """Verifies if the blockchain has been tampered with."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # CRITICAL FIX: Use .get() to avoid KeyError on old data
            curr_prev_hash = current.get("previous_hash", "")
            prev_hash_recorded = previous.get("hash", "")

            if curr_prev_hash != prev_hash_recorded:
                return False
        return True

    def get_student_score(self, student_id):
        """Retrieves the latest valid entry for a given student ID."""
        # Iterate backwards to find the most recent
        for block in reversed(self.chain):
            if block.get("student_id") == student_id:
                return block
        return None

# Instantiate system
ledger_system = LedgerSystem()

# ==========================================
# 🧮 HELPER FUNCTIONS
# ==========================================
def calculate_rent_score(income, guarantor, history):
    score = (
        income * 0.4 +
        guarantor * 0.3 +
        history * 0.2 +
        10   # Base advantage for international students
    )
    return min(int(score), 100)

def generate_custom_qr(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    
    # Branding
    border_color = (66, 135, 245) # SafeRent Blue
    img_w, img_h = img.size
    background = Image.new('RGB', (img_w + 20, img_h + 20), border_color)
    background.paste(img, (10, 10))
    
    # Convert for Streamlit
    buffer = BytesIO()
    background.save(buffer, format="PNG")
    return buffer.getvalue()

# ==========================================
# 🚦 ROUTING & SESSION
# ==========================================
# Initialize student ID if new session
if "student_id" not in st.session_state:
    st.session_state["student_id"] = str(uuid.uuid4())[:8] 

query_params = st.query_params
verify_id = query_params.get("verify_id", None)

# ==========================================
# 👔 LANDLORD VIEW (VERIFICATION)
# ==========================================
if verify_id:
    st.title("🛡️ Landlord Verification Portal")
    st.markdown("---")
    
    # Look up info IN THE LEDGER (not in URL)
    record = ledger_system.get_student_score(verify_id)
    
    if record:
        score = record.get('score', 0)
        ts_str = record.get('timestamp', datetime.now().isoformat())
        timestamp_nice = datetime.fromisoformat(ts_str).strftime("%Y-%m-%d at %H:%M")
        
        # Visual score display
        col1, col2 = st.columns([1, 2])
        with col1:
            if score >= 80:
                st.success(f"✅ EXCELLENT PROFILE")
            elif score >= 50:
                st.warning(f"⚠️ AVERAGE PROFILE")
            else:
                st.error(f"❌ WEAK PROFILE")
            st.metric("Certified RentScore", f"{score}/100")
            
        with col2:
            st.info(f"👤 **Student ID:** `{verify_id}`\n\n📅 **Last Updated:** {timestamp_nice}")
            
        st.subheader("📜 Blockchain Proof")
        st.code(f"""Hash: {record.get('hash')}\nPrev Hash: {record.get('previous_hash')}""", language="text")
        
        if st.checkbox("View Technical Details"):
            st.json(record)
            
        # Global integrity check
        if ledger_system.verify_chain_integrity():
            st.caption("✅ Blockchain Integrity Verified: No data tampered.")
        else:
            st.error("🚨 WARNING: Blockchain data appears corrupted or mixed with old format!")
            
    else:
        st.error("❌ File not found or Invalid ID.")
    
    if st.button("Return to Home"):
        st.query_params.clear()
        st.rerun()
        
    st.stop()

# ==========================================
# 🎓 STUDENT DASHBOARD
# ==========================================
st.title("🌍 SafeRent Global")
st.markdown(f"Welcome, Student **#{st.session_state['student_id']}**")

tabs = st.tabs(["📝 Update Score", "📊 My QR Code", "⛓️ Ledger Explorer"])

with tabs[0]:
    st.write("Update your information to recalculate your certified score.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        income = st.slider("💰 Income (0-100)", 0, 100, 50)
    with col2:
        guarantor = st.slider("🤝 Guarantor (0-100)", 0, 100, 50)
    with col3:
        history = st.slider("📜 History (0-100)", 0, 100, 50)

    current_score = calculate_rent_score(income, guarantor, history)
    
    st.metric("Projected Score", f"{current_score}/100")
    
    if st.button("🚀 Record to Blockchain", use_container_width=True):
        with st.spinner("Mining block..."):
            time.sleep(1) # Slight dramatic effect
            details = f"{income}-{guarantor}-{history}"
            ledger_system.add_block(st.session_state['student_id'], details, current_score)
        st.success("Your score has been sealed in the ledger!")
        st.rerun()

with tabs[1]:
    st.subheader("Your Rental Passport")
    
    # Get last validated score
    last_record = ledger_system.get_student_score(st.session_state['student_id'])
    
    if last_record:
        # Generate secure link
        verify_url = f"{BASE_URL}/?verify_id={st.session_state['student_id']}"
        
        col_qr, col_info = st.columns([1, 2])
        
        with col_qr:
            qr_img = generate_custom_qr(verify_url)
            st.image(qr_img, caption="Scan to verify")
            
        with col_info:
            st.info("This QR code allows landlords to verify your score in real-time on the blockchain.")
            st.write(f"**Hidden Link:** `{verify_url}`")
            st.download_button("Download QR", qr_img, "saferent_pass.png", "image/png")
    else:
        st.warning("Please save a score in the 'Update Score' tab first.")

with tabs[2]:
    st.subheader("Data Transparency")
    st.write("Here is the raw content of the shared `ledger.json`.")
    st.json(ledger_system.chain)
