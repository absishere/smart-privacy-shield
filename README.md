<div align="center">

# 🛡️ Smart Privacy Shield

**A next-gen, decentralized, stateless privacy SaaS for your most sensitive images.**

![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![AWS S3](https://img.shields.io/badge/AWS_S3-Private_Bucket-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Ethereum](https://img.shields.io/badge/Ethereum_ERC--721-NFT_Key_Store-3C3C3D?style=for-the-badge&logo=Ethereum&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-Hardhat-363636?style=for-the-badge&logo=solidity)

</div>

---

## ✨ What it Does

Smart Privacy Shield encrypts the sensitive regions of your images (faces, text, IDs) using **AI-detected ROI + AES-256**, stores the payload exclusively on **AWS S3**, and gates access using **ERC-721 NFTs on the Ethereum blockchain**. Decryption is 100% **in-memory** — no decrypted image is ever written to disk or cloud.

---

## 🚀 Core Features

| Feature | Description |
|---|---|
| 🤖 **AI Region Detection** | OpenCV + MediaPipe + EasyOCR auto-detect faces, eyes, and text in uploaded images |
| 🔐 **AES-256 Stateless Encryption** | Only the sensitive regions are encrypted; keys are stored on-chain, never on a server |
| ☁️ **AWS S3 Cloud Vault** | Encrypted payloads stored in a **private S3 bucket**, scoped per wallet address |
| ⛓️ **NFT-Gated Access** | An ERC-721 NFT acts as the decryption key — you must own it to decrypt |
| 🧠 **In-Memory Decryption** | Decryption runs entirely in server RAM (ByteStream), result returned as Base64 — never saved |
| ⏱️ **60-Second Auto-Shred** | Decrypted image self-destructs from the browser's memory after 60 seconds |
| 🖼️ **Image-in-Image Steganography** | Uses 2-bit LSB to hide an encrypted payload inside a cover image visually |
| 🎯 **Receiver Airdrop** | Mint the access NFT directly to a receiver's wallet — no gas from the sender |
| 🗑️ **Shred from Cloud** | Ownership-verified permanent deletion of both the image and `.roi` metadata from S3 |
| 📋 **Wallet Copy** | Click your wallet address in the sidebar to copy it instantly |

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                          USER (MetaMask Wallet)                        │
└────────────────┬───────────────────────────────────────────────────────┘
                 │ connects via ethers.js
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    React + Vite Dashboard (Port 5173)                  │
│  WalletConnect → UploadDashboard | Vault | SendSecret | ImageUpload   │
└────────────────┬───────────────────────────────────────────────────────┘
                 │ REST API (axios, multipart/form-data)
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Port 8000)                        │
│                                                                        │
│  /process-image  ──► AI Detect ──► AES-256 Encrypt ──► Mint NFT       │
│                                          │                             │
│  /decrypt        ──► Verify NFT ──► Fetch S3 Bytes ──► RAM Decrypt    │
│                                                                        │
│  /delete-image   ──► Verify NFT ──► S3 Delete (img + .roi)            │
│  /covers         ──► List cover images from backend/images/covs/       │
│  /user-images    ──► List S3 objects scoped to wallet address          │
│  /chain-status   ──► Check Ganache + Contract connectivity             │
└────────┬─────────────────────────────────────┬──────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────┐                 ┌─────────────────────────┐
│  AWS S3 (Private│                 │    Ganache + Hardhat     │
│  Bucket)        │                 │    ERC-721 NFT Contract  │
│                 │                 │    PrivacyShield.sol     │
│  encrypted/     │                 │    ─ safeMint(wallet,key)│
│  ├─ {wallet}/   │                 │    ─ ownerOf(tokenId)    │
│  │   └─ img.png │                 │    ─ getKey(tokenId)     │
│  └─ {wallet}/   │                 │       (owner-only)       │
│      └─ img.roi │                 └─────────────────────────┘
│  stego/         │
│  └─ {wallet}/   │
└─────────────────┘
```

---

## 📂 Repository Structure

```
smart-privacy-shield/
│
├── backend/                    # Python FastAPI Backend
│   ├── main.py                 # API endpoints & request orchestration
│   ├── encrypt.py              # AES-256 encryption + decrypt_image_stream
│   ├── image_utils.py          # OpenCV + MediaPipe + EasyOCR ROI detection
│   ├── stego.py                # 2-bit LSB image-in-image steganography
│   ├── cloud_utils.py          # AWS S3: upload, fetch bytes, list, delete
│   ├── blockchain_utils.py     # web3.py: mint NFT, get key, verify ownership
│   ├── pyproject.toml          # Poetry dependencies (Python >=3.10,<3.12)
│   ├── requirements.txt        # Pip-style dependency list
│   └── images/covs/            # Pre-set cover images for steganography
│
├── frontend/                   # React + Vite Frontend
│   └── src/
│       ├── App.jsx             # Sidebar shell & wallet state management
│       ├── index.css           # Glassmorphism dark-mode design system
│       ├── main.jsx            # React entry point
│       └── components/
│           ├── WalletConnect.jsx      # MetaMask ethers.js connection
│           ├── UploadDashboard.jsx    # Encrypt & upload workflow UI
│           ├── Vault.jsx              # S3 image grid, decrypt, shred
│           ├── SendSecret.jsx         # Steganography + receiver airdrop UI
│           └── ImageUpload.jsx        # Legacy single-image upload component
│
├── blockchain/                 # Hardhat + Solidity
│   ├── contracts/
│   │   └── PrivacyShield.sol   # ERC-721 + tokenToKey mapping
│   ├── scripts/                # Deployment scripts
│   └── ignition/               # Hardhat Ignition modules
│
└── tests/                      # Backend test scripts
    └── test_stego.py
```

---

## ⚙️ Getting Started

### Prerequisites

- **Python** `>=3.10, <3.12`
- **Node.js** `v16+` and npm
- **MetaMask** browser extension
- **Ganache** running on `http://127.0.0.1:7545`
- **AWS account** with a private S3 bucket

---

### 1. 🔗 Blockchain Setup

```bash
cd blockchain
npm install
npx hardhat compile

# Deploy to local Ganache
npx hardhat ignition deploy ./ignition/modules/PrivacyShield.js --network localhost
```

After deployment, note the **contract address** and **ABI** — they go into `address.txt` and `abi.json`.

---

### 2. 🐍 Backend Setup

```bash
cd backend
# Using Poetry (recommended)
poetry install
poetry run uvicorn main:app --reload

# Or using pip
pip install -r requirements.txt
uvicorn main:app --reload
```

Create `backend/.env` (**DO NOT COMMIT**):

```env
# Blockchain
GANACHE_URL=http://127.0.0.1:7545
CHAIN_ID=1337
CONTRACT_ADDRESS=0xYourDeployedContractAddress
ADMIN_PRIVATE_KEY=0xYourGanacheAccountPrivateKey
ADMIN_ADDRESS=0xYourGanacheAccountAddress

# AWS S3
AWS_ACCESS_KEY=your_access_key_id
AWS_SECRET_KEY=your_secret_access_key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your-private-bucket-name
```

---

### 3. ⚛️ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Navigate to **`http://localhost:5173`**, connect MetaMask, and enter the Shield! 🛡️

---

## 🔁 How the Flows Work

### Upload (Secure Encrypt & Store)
1. User selects image → sent to `POST /process-image`
2. AI (`image_utils.py`) detects faces/text → generates bounding boxes
3. `encrypt.py` slices & AES-256 encrypts each ROI → saves `.roi` metadata
4. `blockchain_utils.py` mints NFT to user wallet with AES key stored on-chain
5. `cloud_utils.py` uploads `encrypted/{wallet}/image.png` + `.roi` to private S3
6. All local temp files purged from `tmp_processing/`

### Decrypt (In-Memory, Zero-Trace)
1. User clicks Decrypt → enters Token ID → `POST /decrypt`
2. Backend checks `contract.ownerOf(tokenId)` == wallet address
3. Backend fetches AES key from `contract.getKey(tokenId)` (owner-only function)
4. Encrypted image bytes + `.roi` bytes streamed from S3 directly into server RAM
5. `decrypt_image_stream` reconstructs & decrypts fully in memory
6. Returns `data:image/jpeg;base64,...` string — shown for **60 seconds** then erased

### Send Secret (Steganography + Airdrop)
1. User selects secret image + a cover image (preset dropdown OR custom upload)
2. Backend encrypts secret image, then `stego.py` injects it into cover's LSB pixels
3. Stego image uploaded to `stego/{receiver_wallet}/image.png` on S3
4. NFT minted **directly to the receiver's wallet** by the backend relayer
5. Receiver opens their Vault — the cover image is there, ready to decrypt

### Shred from Cloud
1. User clicks 🗑️ Shred → enters Token ID → `DELETE /delete-image`
2. Backend verifies NFT ownership on-chain
3. Both `image.png` and `image.png.roi` permanently deleted from S3
4. Vault grid refreshes automatically

---

## 🔒 Security Design

- **No plaintext keys on server** — AES keys live exclusively on the blockchain inside the NFT
- **No decrypted files on disk** — decryption is 100% in-server RAM via ByteStream
- **Per-wallet S3 namespacing** — `encrypted/{wallet}/` ensures users only see their own files
- **NFT ownership verified on every action** — decrypt, delete, all require `ownerOf` check
- **`UnicodeDecodeError` guard** — wrong Token ID triggers a `403 Invalid Token ID` response
- **60-second memory shred** — browser auto-clears the Base64 decrypted image state

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, ethers.js v6, axios |
| Backend | Python 3.11, FastAPI, uvicorn, Poetry |
| AI / Vision | OpenCV, MediaPipe, EasyOCR |
| Cryptography | AES-256 (PyCryptodome), NumPy |
| Steganography | 2-bit LSB (NumPy + Pillow) |
| Blockchain | Solidity, Hardhat, web3.py, Ganache |
| Cloud Storage | AWS S3 (boto3), Presigned URLs |
| Standards | ERC-721 (OpenZeppelin) |

---

<div align="center">

*Built for the protection of privacy in the modern digital age.*

</div>
