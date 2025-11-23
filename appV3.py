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
BASE_URL = "https://safrent-global.streamlit.app" # Remplace par ton URL finale

# ==========================================
# 🔐 BLOCKCHAIN LOGIC
# ==========================================
class LedgerSystem:
    def __init__(self):
        self.filename = LEDGER_FILE
        self.chain = self.load_chain()

    def load_chain(self):
        """Charge le registre. Si erreur ou fichier vide, retourne une liste vide."""
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_chain(self):
        """Sauvegarde le registre dans le fichier JSON."""
        with open(self.filename, "w") as f:
            json.dump(self.chain, f, indent=4)

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def add_block(self, student_id, details, score):
        """Ajoute un bloc avec hachage chaîné (Vrai Blockchain)."""
        previous_block = self.get_last_block()
        prev_hash = previous_block["hash"] if previous_block else "0"
        
        timestamp = datetime.now().isoformat()
        
        # Création du payload à hacher (Inclut le hash précédent pour la sécurité)
        block_content = f"{student_id}{details}{timestamp}{prev_hash}"
        new_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        block = {
            "index": len(self.chain) + 1,
            "timestamp": timestamp,
            "student_id": student_id,
            "type": "score_update",
            "details": details, # ex: "50-50-50"
            "score": score,     # On stocke le score calculé
            "previous_hash": prev_hash,
            "hash": new_hash
        }
        
        self.chain.append(block)
        self.save_chain()
        return block

    def verify_chain_integrity(self):
        """Vérifie si la blockchain a été altérée."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current["previous_hash"] != previous["hash"]:
                return False
        return True

    def get_student_score(self, student_id):
        """Récupère la dernière entrée valide pour un étudiant donné."""
        # On parcourt à l'envers pour avoir le plus récent
        for block in reversed(self.chain):
            if block.get("student_id") == student_id:
                return block
        return None

# Instantiation du système
ledger_system = LedgerSystem()

# ==========================================
# 🧮 HELPER FUNCTIONS
# ==========================================
def calculate_rent_score(income, guarantor, history):
    score = (
        income * 0.4 +
        guarantor * 0.3 +
        history * 0.2 +
        10   # Bonus étudiant international
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
    
    # Conversion pour Streamlit
    buffer = BytesIO()
    background.save(buffer, format="PNG")
    return buffer.getvalue()

# ==========================================
# 🚦 ROUTING & SESSION
# ==========================================
# On initialise un ID étudiant s'il n'existe pas (Session)
if "student_id" not in st.session_state:
    st.session_state["student_id"] = str(uuid.uuid4())[:8] # ID court

query_params = st.query_params
verify_id = query_params.get("verify_id", None)

# ==========================================
# 👔 LANDLORD VIEW (VERIFICATION)
# ==========================================
if verify_id:
    st.title("🛡️ Portail de Vérification Propriétaire")
    st.markdown("---")
    
    # On cherche l'info DANS LE LEDGER (pas dans l'URL)
    record = ledger_system.get_student_score(verify_id)
    
    if record:
        score = record['score']
        timestamp_nice = datetime.fromisoformat(record['timestamp']).strftime("%d/%m/%Y à %H:%M")
        
        # Affichage visuel du score
        col1, col2 = st.columns([1, 2])
        with col1:
            if score >= 80:
                st.success(f"✅ EXCELLENT DOSSIER")
            elif score >= 50:
                st.warning(f"⚠️ DOSSIER MOYEN")
            else:
                st.error(f"❌ DOSSIER FAIBLE")
            st.metric("RentScore Certifié", f"{score}/100")
            
        with col2:
            st.info(f"👤 **ID Étudiant :** `{verify_id}`\n\n📅 **Dernière mise à jour :** {timestamp_nice}")
            
        st.subheader("📜 Preuve Blockchain")
        st.code(f"""Hash: {record['hash']}\nPrev Hash: {record['previous_hash']}""", language="text")
        
        if st.checkbox("Voir les détails techniques"):
            st.json(record)
            
        # Vérification d'intégrité globale
        if ledger_system.verify_chain_integrity():
            st.caption("✅ Intégrité de la Blockchain vérifiée : Aucune donnée altérée.")
        else:
            st.error("🚨 ALERTE : La Blockchain semble corrompue !")
            
    else:
        st.error("❌ Dossier introuvable ou ID invalide.")
    
    if st.button("Retour à l'accueil"):
        st.query_params.clear()
        st.rerun()
        
    st.stop()

# ==========================================
# 🎓 STUDENT DASHBOARD
# ==========================================
st.title("🌍 SafeRent Global")
st.markdown(f"Bienvenue, étudiant **#{st.session_state['student_id']}**")

tabs = st.tabs(["📝 Mettre à jour mon Score", "📊 Mon QR Code", "⛓️ Explorer le Ledger"])

with tabs[0]:
    st.write("Mettez à jour vos informations pour recalculer votre score certifié.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        income = st.slider("💰 Revenus (0-100)", 0, 100, 50)
    with col2:
        guarantor = st.slider("🤝 Garant (0-100)", 0, 100, 50)
    with col3:
        history = st.slider("📜 Historique (0-100)", 0, 100, 50)

    current_score = calculate_rent_score(income, guarantor, history)
    
    st.metric("Score Prévisionnel", f"{current_score}/100")
    
    if st.button("🚀 Enregistrer dans la Blockchain", use_container_width=True):
        with st.spinner("Minage du bloc en cours..."):
            time.sleep(1) # Petit effet dramatique
            details = f"{income}-{guarantor}-{history}"
            ledger_system.add_block(st.session_state['student_id'], details, current_score)
        st.success("Votre score a été scellé dans le registre !")
        st.rerun()

with tabs[1]:
    st.subheader("Votre Passeport Locatif")
    
    # On récupère le dernier score validé de cet étudiant
    last_record = ledger_system.get_student_score(st.session_state['student_id'])
    
    if last_record:
        # Génération du lien sécurisé (on passe l'ID, pas le score !)
        verify_url = f"{BASE_URL}/?verify_id={st.session_state['student_id']}"
        
        col_qr, col_info = st.columns([1, 2])
        
        with col_qr:
            qr_img = generate_custom_qr(verify_url)
            st.image(qr_img, caption="Scannez pour vérifier")
            
        with col_info:
            st.info("Ce QR code permet au propriétaire de vérifier votre score en temps réel sur la blockchain.")
            st.write(f"**Lien caché :** `{verify_url}`")
            st.download_button("Télécharger mon QR", qr_img, "saferent_pass.png", "image/png")
    else:
        st.warning("Veuillez d'abord enregistrer un score dans l'onglet 'Mettre à jour'.")

with tabs[2]:
    st.subheader("Transparence des données")
    st.write("Voici le contenu brut du fichier `ledger.json` partagé.")
    st.json(ledger_system.chain)
