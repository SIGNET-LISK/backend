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
    description: str = Form(...)
):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Generate pHash
        if file.content_type.startswith("video") or file.filename.endswith((".mp4", ".mov", ".avi")):
            p_hash = get_video_phash(temp_path)
        else:
            with open(temp_path, "rb") as f:
                p_hash = get_image_phash(f.read())
                
        # Register on Blockchain
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
