from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.hashing import get_image_phash, get_video_phash
from indexer.search import get_verifier
from indexer.db import SessionLocal
from models.content import Content
import shutil
import os
import tempfile

router = APIRouter()
verifier = get_verifier()

@router.post("/verify")
async def verify_content(
    file: UploadFile = File(None),
    link: str = Form(None)
):
    if not file and not link:
        raise HTTPException(status_code=400, detail="Either file or link must be provided")

    temp_dir = tempfile.mkdtemp()
    p_hash = None
    
    try:
        if file:
            temp_path = os.path.join(temp_dir, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            if file.content_type.startswith("video") or file.filename.endswith((".mp4", ".mov", ".avi")):
                p_hash = get_video_phash(temp_path)
            else:
                with open(temp_path, "rb") as f:
                    p_hash = get_image_phash(f.read())
        
        # TODO: Implement Link handling (yt-dlp) if needed here, similar to bot
        
        if not p_hash:
             raise HTTPException(status_code=400, detail="Could not generate hash")

        # Search in ANN
        matches = verifier.search(p_hash, k=1)
        
        if not matches:
            return {
                "status": "UNVERIFIED",
                "pHash": p_hash,
                "message": "No matching content found."
            }
            
        best_match_phash, distance = matches[0]
        
        # Fetch details from DB
        db = SessionLocal()
        content = db.query(Content).filter(Content.phash == best_match_phash).first()
        db.close()

        if not content:
             return {
                "status": "UNVERIFIED",
                "pHash": p_hash,
                "message": "Match found in index but not in DB (inconsistent state)."
            }
            
        threshold = int(os.getenv("HAMMING_THRESHOLD", 25))
        is_verified = distance <= threshold
        
        return {
            "status": "VERIFIED" if is_verified else "UNVERIFIED",
            "pHash_input": p_hash,
            "pHash_match": best_match_phash,
            "hamming_distance": int(distance),
            "publisher": content.publisher,
            "title": content.title,
            "txHash": content.txhash,
            "explorer_link": f"https://sepolia-blockscout.lisk.com/tx/{content.txhash if content.txhash.startswith('0x') else '0x' + content.txhash}",
            "message": "Content is authentic." if is_verified else "Content is different."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir)
