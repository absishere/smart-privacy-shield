from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from blockchain_utils import get_contract

from image_utils import process_image 

app = FastAPI(title="Smart Privacy Shield API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Folders
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Mount Static Files (So we can see images later)
app.mount("/static", StaticFiles(directory="processed"), name="static")

@app.get("/")
def read_root():
    return {"message": "Privacy Shield API is running (Waiting for AI Models)"}

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

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # 1. Save Original
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    # 2. Define Output Path
    processed_filename = f"protected_{file.filename}"
    output_location = f"{PROCESSED_DIR}/{processed_filename}"

    # 3. CALL YOUR AI FUNCTION HERE
    # This runs the MediaPipe + EasyOCR logic you just wrote
    success, message = process_image(file_location, output_location)

    if success:
        return {
            "status": "success",
            "message": message,
            "original": file.filename,
            "processed_url": f"http://127.0.0.1:8000/static/{processed_filename}"
        }
    else:
        return {"status": "error", "message": message}
