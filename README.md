# 🌍 SafeRent Global — Blockchain Rental Verification

**SafeRent Global** is a decentralized application (dApp) prototype designed to help international students prove their reliability to landlords. It uses a **simulated blockchain ledger** and **cryptographic signatures** to certify a "RentScore," validated by a trusted institution (e.g., NEOMA BS).

![Status](https://img.shields.io/badge/Status-Live-green) ![Tech](https://img.shields.io/badge/Built%20With-Streamlit-red)

## 🚀 Overview

International students often lack a local guarantor or rental history. SafeRent Global solves this by:
1.  **Calculating a RentScore** based on income, guarantor strength, and history.
2.  **Validating** this data via a trusted Node (University/Validator).
3.  **Storing** the validated score on an immutable JSON ledger (Blockchain logic).
4.  **Sharing** the result via a tamper-proof QR Code and Digital Certificate.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/saferent-global.git](https://github.com/your-username/saferent-global.git)
    cd saferent-global
    ```

2.  **Install dependencies:**
    Ensure you have Python installed, then run:
    ```bash
    pip install streamlit qrcode[pil] ecdsa
    ```
    *Note: The `requirements.txt` file should contain: `streamlit`, `qrcode`, `pillow`, `ecdsa`.*

3.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

## 🛠️ Usage Guide

### 1. 🎓 Student View (Default)
* **Update Profile:** Adjust income, guarantor, and history sliders to calculate a projected score.
* **Request Validation:** Click "Send for Validation" to submit your profile to the University Node.
* **Notifications:** Receive real-time updates (Accepted/Rejected) upon refreshing.
* **My QR Code:** Once validated, download your **Digital Certificate** (PDF/PNG) containing your cryptographic proof.

### 2. 🔐 Validator View (University Staff)
* **Access:** Open the Sidebar > "Staff / Validator Access".
* **Password:** `admin`
* **Dashboard:** View pending student requests.
* **Action:** * **✅ Accept:** Signs the data with a Private Key and mines a block to the ledger.
    * **❌ Reject:** Sends a rejection notification to the student.

### 3. 🛡️ Landlord View (Verification)
* **Scan:** Scan the student's QR code.
* **Verify:** The app instantly retrieves the data from the blockchain.
* **Analysis:** View a colored risk assessment (Excellent/Average/Risky) and verify the cryptographic signature.

## 📂 Project Structure

* `app.py`: Main application code (Streamlit interface + Blockchain logic).
* `ledger.json`: The immutable ledger storing validated blocks.
* `pending.json`: Temporary storage for requests awaiting validation.
* `accepted.json` / `rejected.json`: Notification system files.
* `requirements.txt`: List of Python libraries required.

## 🔐 Security Features

* **ECDSA Signatures:** Every validated block is cryptographically signed by the Validator's private key.
* **Hash Chaining:** Each block contains the hash of the previous block, preventing ledger tampering.
* **Identity Protection:** Landlords look up data via Student ID, preventing URL spoofing.

---
*Created for the SafeRent Global Project.*
