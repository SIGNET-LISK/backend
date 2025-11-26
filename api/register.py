from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from services.hashing import get_image_phash, get_video_phash
from services.blockchain import SignetContract
import shutil
import os
import tempfile

router = APIRouter()
contract = SignetContract()

@router.post("/register-content")
async def register_content(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    publisher_address: str = Form(None)  # Address dari wallet yang connect di frontend
):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename or "uploaded_file")
    
    try:
        # Validate publisher if address provided
        if publisher_address:
            # Normalize address (lowercase, checksum)
            from web3 import Web3
            publisher_address = Web3.to_checksum_address(publisher_address)
            
            # Check if address is authorized publisher
            is_authorized = contract.is_publisher_authorized(publisher_address)
            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=f"Address {publisher_address} is not authorized as publisher. Please contact admin to add you as publisher."
                )
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Generate pHash
        if file.content_type and file.content_type.startswith("video") or (file.filename and file.filename.endswith((".mp4", ".mov", ".avi"))):
            p_hash = get_video_phash(temp_path)
        else:
            with open(temp_path, "rb") as f:
                p_hash = get_image_phash(f.read())
                
        # Register on Blockchain (using relayer wallet from .env)
        tx_hash = contract.register_content(p_hash, title, description)
        
        return {
            "status": "SUCCESS",
            "pHash": p_hash,
            "txHash": tx_hash,
            "message": "Content registered successfully. Indexer will pick it up shortly."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir)
