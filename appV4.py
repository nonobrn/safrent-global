import streamlit as st
import json
import hashlib
import time
import qrcode
import uuid
from io import BytesIO
from PIL import Image
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError

# ==========================================
# ⚙️ CONFIGURATION & KEYS
# ==========================================
st.set_page_config(page_title="SafeRent Global", page_icon="🌍", layout="centered")

LEDGER_FILE = "ledger.json"
PENDING_FILE = "pending.json"
BASE_URL = "https://safrent-global.streamlit.app" # Remplace par ton URL

# --- 🔐 NODE CONFIGURATION (SIMULATION) ---
# Dans un vrai projet, la clé privée est dans st.secrets, jamais dans le code.
# Pour la démo, voici des clés générées pour "University Node A".

# Clé Publique (Connue de tous, permet de vérifier la signature)
NODE_PUBLIC_KEY = "9a4f6760d7502c4689c1d05452f1e843577d6108169996e3871404c0032b4987771746654a106e232b7724227918ba18"

# Clé Privée (Connue SEULEMENT du validateur, permet de signer)
# Normalement cachée, je la mets ici pour que tu puisses tester le rôle validateur tout de suite.
NODE_PRIVATE_KEY = "5f2f545137803732049615555430263303681440854652285552358825835688"
NODE_NAME = "University of Reims"

# ==========================================
# 🧱 DATA SYSTEMS (Ledger & Pending)
# ==========================================

class DataManager:
    """Gère le chargement et la sauvegarde des fichiers JSON."""
    @staticmethod
    def load_data(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def save_data(filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

class LedgerSystem:
    def __init__(self):
        self.chain = DataManager.load_data(LEDGER_FILE)

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def add_signed_block(self, pending_req, signature, validator_name):
        """Ajoute un bloc validé et signé dans la Blockchain."""
        previous_block = self.get_last_block()
        prev_hash = previous_block.get("hash", "0") if previous_block else "0"
        
        timestamp = datetime.now().isoformat()
        
        # Le contenu critique qui lie le bloc
        block_content = f"{pending_req['student_id']}{pending_req['details']}{timestamp}{prev_hash}"
        block_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        block = {
            "index": len(self.chain) + 1,
            "timestamp": timestamp,
            "student_id": pending_req['student_id'],
            "type": "verified_score",
            "details": pending_req['details'],
            "score": pending_req['score'],
            "validator": validator_name,
            "signature": signature,      # ✍️ La preuve cryptographique
            "previous_hash": prev_hash,
            "hash": block_hash
        }
        
        self.chain.append(block)
        DataManager.save_data(LEDGER_FILE, self.chain)
        return block

    def get_student_score(self, student_id):
        for block in reversed(self.chain):
