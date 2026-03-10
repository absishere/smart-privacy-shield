# 🛡️ Smart Privacy Shield

![Smart Privacy Shield](https://img.shields.io/badge/Status-Beta-success?style=for-the-badge) 
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![AWS S3](https://img.shields.io/badge/AWS_S3-569A31?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Ethereum](https://img.shields.io/badge/Ethereum-3C3C3D?style=for-the-badge&logo=Ethereum&logoColor=white)

**Smart Privacy Shield** is a next-generation decentralized privacy SaaS application. It combines dynamic AI region encryption, blockchain-based access control (NFTs), and stateless secure memory decryption to ensure that your sensitive images remain truly yours. 

## ✨ Key Features

- **Stateless Cloud Architecture:** Encrypted image payloads and metadata are stored exclusively on AWS S3. Decryption happens entirely in your local RAM—no decrypted files are ever saved to disk permanently.
- **Blockchain Key Management:** AES-256 encryption keys are generated dynamically and securely tethered to an ERC-721 Token (NFT) on the blockchain. You must hold the NFT to decrypt the image.
- **Image-in-Image Steganography:** Hide highly sensitive encrypted data payloads inside regular, innocent-looking cover images using advanced 2-bit LSB steganography algorithms.
- **"Shred from Cloud":** Complete autonomy over your data. With one click, prove your wallet ownership and permanently obliterate the file and metrics directly from the AWS S3 buckets.
- **Receiver Payload Transfer:** Airdrop hidden decrypted payloads to a receiver. The system embeds the secret in a selected cover image and directly mints the access NFT into the receiver's Ethereum wallet.

## 🏗️ The Architecture

1. **Upload Phase:**
    - AI dynamically detects ROI (Region of Interest - faces/text) using OpenCV/Haar Cascades.
    - Slices ROI, encrypts pixels with randomized AES-256.
    - Mints dynamic Blockchain Key to user wallet.
    - Pushes encrypted payload to AWS S3, deleting all local cached temporary files.

2. **Secure Vault Phase:**
    - Fetches the payload securely from AWS S3 via ephemeral URL links.
    - Queries the blockchain for token access via a MetaMask challenge.
    - Decrypts the image entirely via in-memory ByteStreams.
    - Self-destructs the payload from RAM after a secure 60-second viewing window.

## 🚀 Getting Started

### Prerequisites

- Node.js (v16+)
- Python (v3.10 to v3.12)
- MetaMask Extension
- Ganache (Local Ethereum Blockchain)
- AWS SDK Credentials with active S3 bucket access.

### 1. Blockchain Setup

Use Hardhat to securely deploy the Smart Contract locally:

```bash
cd blockchain
npm install
npx hardhat compile
npx hardhat ignition deploy ./ignition/modules/PrivacyShield.js --network localhost
```
*Note: Make sure Ganache is running on `http://127.0.0.1:7545` before deploying!*

### 2. Backend (FastAPI) Setup

Configure your Python virtual environment and `.env` secrets:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

Create a `.env` file in the `/backend` folder. **DO NOT COMMIT THIS FILE.** Ensure it mirrors `.env.example`:

```env
GANACHE_URL=http://127.0.0.1:7545
CHAIN_ID=1337

# Ensure you have your Contract Address and private deployment keys here
CONTRACT_ADDRESS=0xYourDeployedAddress
ADMIN_PRIVATE_KEY=your_private_key
ADMIN_ADDRESS=your_wallet_address

# AWS Architecture Requirements
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your_s3_bucket_name
```

Run the robust Backend server:
```bash
poetry run uvicorn main:app --reload
```

### 3. Frontend (React) Setup

Deploy the sleek Frontend dashboard:

```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`. Connect your MetaMask wallet, and enter the Vault! 🕵️

## 📁 Repository Structure

```graphql
smart-privacy-shield/
├── backend/            # Python FastAPI, Cloud Integrations, and AI Crypto Logic
│   ├── main.py         # Primary Endpoints (/process-image, /decrypt, /delete-image)
│   ├── cloud_utils.py  # AWS S3 Cloud Architecture hooks
│   ├── encrypt.py      # Core stateless AES-256 Stream operations
│   ├── stego.py        # Image-in-Image 2-Bit LSB hiders
│   └── blockchain_utils# Web3 Py Hooks for NFT key querying
│
├── frontend/           # React + Vite Dashboard
│   ├── src/components/
│   │   ├── Vault.jsx         # S3 File display and memory shredder UI
│   │   ├── SendSecret.jsx    # Complex Stego+Receiver Flow architecture UI
│   │   └── WalletConnect.jsx # Eth Web3 Ethers.js integration
│   └── index.css       # Fully custom aesthetic glassmorphism UI rulesets
│
└── blockchain/         # Hardhat and Solidity Contracts
    └── contracts/
        └── PrivacyShield.sol # Core ERC-721 implementation handling encryption keys map.
```

## 🔒 Security Commitments
Any issues or proposed architectural upgrades relating to stateless memory tracking or AES algorithm hashing improvements should be formally routed through GitHub Issues.

---
*Built tightly for the protection of privacy in the modern digital age.*
