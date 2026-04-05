from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
from blockchain_utils import get_contract, mint_privacy_nft, record_access_fire_and_forget
from image_utils import detect_sensitive_regions
from encrypt import encrypt_image, decrypt_image, decrypt_image_stream
from stego import hide_secret_image, reveal_secret_image, COVERS_DIR
import shutil
from cloud_utils import upload_to_s3, download_from_s3, list_user_images, get_s3_bytes, delete_from_s3, recover_pristine_version
import base64
import io
import hashlib

app = FastAPI(title="Smart Privacy Shield API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use a single temporary directory for all processing steps before S3 upload/deletion
TEMP_DIR = Path("tmp_processing")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True) # Needed so get_covers works

@app.get("/")
def read_root():
    return {"message": "Privacy Shield API is running"}

@app.get("/covers")
def get_covers():
    if not COVERS_DIR.exists():
        return {"covers": []}
    covers = [f.name for f in COVERS_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg"]]
    return {"covers": covers}

@app.get("/chain-status")
def check_chain():
    w3, contract = get_contract()
    if contract:
        try:
            name = contract.functions.name().call()
            return {"status": "connected", "contract_name": name, "address": contract.address}
        except Exception as e:
            return {"status": "error", "details": str(e)}
    return {"status": "failed_to_load_contract"}

@app.get("/user-images")
def get_user_images(wallet_address: str):
    """Returns all available encrypted/stego images for this user from S3."""
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
    images = list_user_images(wallet_address)
    return {"status": "success", "images": images}

@app.post("/process-image")
async def process_image(
    file: UploadFile = File(...), 
    wallet_address: str = Form(""),
    is_stego_mode: bool = Form(False),
    cover_image_name: str = Form("default_cover.png"),
    custom_cover: UploadFile | None = File(None)
):
    try:
        # 1. Save the incoming Secret Image temporarily
        input_path = TEMP_DIR / file.filename
        with open(input_path, "wb") as f:
            f.write(await file.read())

        # 2. AI Detection & ROI Encryption
        # Detect faces/text and create the 'encrypted' version of the secret image
        boxes = detect_sensitive_regions(input_path) 
        encryption_result = encrypt_image(
            filename=file.filename,
            boxes=boxes,
            input_dir=TEMP_DIR,
            output_dir=TEMP_DIR
        )

        # Phase 4: S3 ROI metadata upload
        roi_meta_path = TEMP_DIR / f"{file.filename}.roi"
        final_upload_path = TEMP_DIR / file.filename
        
        # 4. PHASE 1: Image-in-Image Steganography (Conditional)
        if is_stego_mode:
            if custom_cover:
                # Save the custom cover safely to the covers directory
                cover_path = COVERS_DIR / custom_cover.filename
                with open(cover_path, "wb") as f:
                    f.write(await custom_cover.read())
                final_cover_name = custom_cover.filename
            else:
                cover_path = COVERS_DIR / cover_image_name
                final_cover_name = cover_image_name
                if not cover_path.exists():
                    raise HTTPException(status_code=400, detail=f"Cover image {cover_image_name} not found in {COVERS_DIR}")

            stego_output_path = TEMP_DIR / f"stego_{file.filename}"
            hide_secret_image(
                cover_path=str(cover_path),
                secret_path=str(TEMP_DIR / file.filename),
                output_path=str(stego_output_path)
            )
            final_upload_path = stego_output_path

        # Calculate SHA-256 hash of the final file to upload
        with open(final_upload_path, "rb") as f:
            file_bytes = f.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 3. MINT THE NFT
        token_id = None
        if wallet_address:
            try:
                token_id = mint_privacy_nft(wallet_address, encryption_result.key, file_hash)
                if token_id is None:
                    raise Exception("Blockchain Minting Failed")
                print(f"[*] NFT Minted! Token ID: {token_id}")
            except Exception as b_err:
                print(f"[!] Blockchain error: {b_err}")
                raise HTTPException(status_code=500, detail=f"Blockchain Error: {str(b_err)}")

        # PHASE 2/4: AWS UPLOAD Image & Metadata
        if is_stego_mode:
            cloud_url = upload_to_s3(final_upload_path, f"stego/{wallet_address}/{file.filename}")
            if roi_meta_path.exists(): upload_to_s3(roi_meta_path, f"stego/{wallet_address}/{file.filename}.roi")
            
            if not cloud_url:
                raise HTTPException(status_code=500, detail="Failed to upload to AWS S3. Check credentials.")
            
            # Temporary local cleanup
            if input_path.exists(): os.remove(input_path)
            if (TEMP_DIR / file.filename).exists(): os.remove(TEMP_DIR / file.filename)
            if roi_meta_path.exists(): os.remove(roi_meta_path)
            if final_upload_path.exists(): os.remove(final_upload_path)

            return {
                "status": "success",
                "mode": "stego",
                "message": f"Secret image hidden in {final_cover_name} and NFT minted!",
                "token_id": token_id,
                "display_url": cloud_url,
                "storage": "AWS S3" if cloud_url else "Error",
                "original": f"stego_{file.filename}"
            }

        # DEFAULT: Feature 1 Only
        cloud_url = upload_to_s3(final_upload_path, f"encrypted/{wallet_address}/{file.filename}")
        if roi_meta_path.exists(): upload_to_s3(roi_meta_path, f"encrypted/{wallet_address}/{file.filename}.roi")
        
        if not cloud_url:
            raise HTTPException(status_code=500, detail="Failed to upload to AWS S3. Check credentials.")
        
        # Temporary local cleanup
        if input_path.exists(): os.remove(input_path)
        if (TEMP_DIR / file.filename).exists(): os.remove(TEMP_DIR / file.filename)
        if roi_meta_path.exists(): os.remove(roi_meta_path)
        
        return {
            "status": "success",
            "mode": "encryption_only",
            "message": f"Image processed. Detected {len(boxes)} sensitive regions.",
            "token_id": token_id,
            "display_url": cloud_url,
            "storage": "AWS S3" if cloud_url else "Error",
            "original": file.filename
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/decrypt")
async def decrypt_image_endpoint(
    filename: str = Form(...), 
    wallet_address: str = Form(...),
    token_id: int = Form(...), # We need the token_id to check specific ownership
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    
    try:
        # 1. Connect to Blockchain
        w3, contract = get_contract()
        if not contract:
            raise HTTPException(status_code=500, detail="Blockchain connection failed")

        # 2. VALIDATION: Check if this wallet owns the specific NFT
        try:
            current_owner = contract.functions.ownerOf(token_id).call()
            # Normalize addresses to checksum format for a fair comparison
            if w3.to_checksum_address(current_owner) != w3.to_checksum_address(wallet_address):
                raise HTTPException(
                    status_code=403, 
                    detail="Access Denied: You do not own the NFT associated with this image."
                )
                
            # Fetch the decryption key directly from the Smart Contract using token_id!    
            encrypted_key = contract.functions.getKey(token_id).call({'from': w3.to_checksum_address(wallet_address)})
            expected_hash = contract.functions.getFileHash(token_id).call({'from': w3.to_checksum_address(wallet_address)})
            
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"Ownership verification failed: {str(e)}")

        print(f"[*] Ownership Verified for {wallet_address}. Decrypting in memory...")
        
        # Dispatch Blockchain Audit Trail (Fire-and-Forget)
        background_tasks.add_task(record_access_fire_and_forget, token_id, wallet_address)

        # 3. Always fetch from Cloud (Strict Cloud-First Architecture)
        if filename.startswith("stego/"):
            s3_image_key = filename
            s3_meta_key = f"{filename}.roi"
            is_stego = True
        elif filename.startswith("encrypted/"):
            s3_image_key = filename
            s3_meta_key = f"{filename}.roi"
            is_stego = False
        else:
            # Fallback for old filename queries
            if filename.startswith("stego_"):
                s3_image_key = f"stego/{filename.replace('stego_', '')}"
                s3_meta_key = f"stego/{filename.replace('stego_', '')}.roi"
                is_stego = True
            else:
                s3_image_key = f"encrypted/{filename}"
                s3_meta_key = f"encrypted/{filename}.roi"
                is_stego = False

        print(f"[*] Fetching {s3_image_key} and metadata from AWS S3 directly to RAM...")
        image_bytes = get_s3_bytes(s3_image_key)
        meta_bytes = get_s3_bytes(s3_meta_key)

        if not image_bytes or not meta_bytes:
            raise HTTPException(status_code=404, detail="Encrypted data or metadata missing from AWS S3.")

        # Tamper Detection
        downloaded_hash = hashlib.sha256(image_bytes).hexdigest()
        if downloaded_hash != expected_hash:
            print(f"⚠️ CRITICAL WARNING: Integrity mismatch for {s3_image_key}. Tampering detected!")
            image_bytes = recover_pristine_version(s3_image_key, expected_hash)
            if not image_bytes:
                raise HTTPException(status_code=409, detail="CRITICAL: File integrity compromised. Tampering detected and recovery failed.")

        # 4. Steganography extraction OR Standard Decryption (In Memory)
        if is_stego:
            # Note: Steganography extraction currently relies on the local disk via numpy/PIL paths 
            # To keep things stateless but functioning, we write to the temp drive JUST for extraction
            # then delete immediately after passing bytes to decrypt_image_stream.
            real_filename = filename.split("/")[-1]
            temp_stego = TEMP_DIR / f"temp_{real_filename}"
            temp_extracted = TEMP_DIR / f"extracted_{real_filename}"
            
            with open(temp_stego, "wb") as f:
                f.write(image_bytes)
                
            reveal_secret_image(str(temp_stego), str(temp_extracted))
            
            with open(temp_extracted, "rb") as f:
                extracted_image_bytes = f.read()
                
            if temp_stego.exists(): os.remove(temp_stego)
            if temp_extracted.exists(): os.remove(temp_extracted)
            
            try:
                decrypted_pil_image = decrypt_image_stream(
                    image_bytes=extracted_image_bytes,
                    metadata_bytes=meta_bytes,
                    key=encrypted_key
                )
            except UnicodeDecodeError:
                raise HTTPException(status_code=403, detail="Invalid Token ID. The blockchain key does not match this image.")
        else:
            try:
                decrypted_pil_image = decrypt_image_stream(
                    image_bytes=image_bytes,
                    metadata_bytes=meta_bytes,
                    key=encrypted_key
                )
            except UnicodeDecodeError:
                raise HTTPException(status_code=403, detail="Invalid Token ID. The blockchain key does not match this image.")
            
        # 5. Convert to Base64 to send to Frontend
        buffered = io.BytesIO()
        decrypted_pil_image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return {
            "status": "success",
            "message": "Image decrypted securely in memory. No traces left.",
            "image_data": f"data:image/jpeg;base64,{img_str}" # Sends raw data, no URL!
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/delete-image")
async def delete_image_endpoint(
    filename: str = Form(...), 
    wallet_address: str = Form(...),
    token_id: int = Form(...)
):
    try:
        # 1. Verify Ownership (Same strict check as decryption)
        w3, contract = get_contract()
        current_owner = contract.functions.ownerOf(token_id).call()
        if w3.to_checksum_address(current_owner) != w3.to_checksum_address(wallet_address):
            raise HTTPException(status_code=403, detail="Access Denied: You do not own this NFT.")

        # 2. Determine S3 Keys
        if filename.startswith("stego/") or filename.startswith("encrypted/"):
            s3_image_key = filename
            s3_meta_key = f"{filename}.roi"
        elif filename.startswith("stego_"):
            s3_image_key = f"stego/{filename.replace('stego_', '')}"
            s3_meta_key = f"stego/{filename.replace('stego_', '')}.roi"
        else:
            s3_image_key = f"encrypted/{filename}"
            s3_meta_key = f"encrypted/{filename}.roi"

        # 3. Delete from AWS S3
        img_deleted = delete_from_s3(s3_image_key)
        meta_deleted = delete_from_s3(s3_meta_key)

        if not img_deleted:
            raise HTTPException(status_code=500, detail="Failed to delete image from AWS S3.")

        return {"status": "success", "message": "Image and metadata permanently shredded from the cloud."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-trail/{token_id}")
async def get_audit_trail(token_id: int, wallet_address: str):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
        
    try:
        w3, contract = get_contract()
        if not contract:
            raise HTTPException(status_code=500, detail="Blockchain connection failed")
            
        current_owner = contract.functions.ownerOf(token_id).call()
        if w3.to_checksum_address(current_owner) != w3.to_checksum_address(wallet_address):
            raise HTTPException(status_code=403, detail="Access Denied: You do not own this NFT.")
            
        records = contract.functions.getAuditTrail(token_id).call({'from': w3.to_checksum_address(wallet_address)})
        
        import datetime
        formatted_records = []
        for r in records:
            dt = datetime.datetime.fromtimestamp(r[1]).isoformat()
            formatted_records.append({
                "accessor": r[0],
                "timestamp": dt,
                "action": r[2]
            })
        
        return {"status": "success", "history": formatted_records[::-1]} # Return newest first
    except HTTPException as he:
        raise he
    except Exception as e:
        return {"status": "error", "message": str(e)}
