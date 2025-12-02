from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.hashing import get_image_phash, get_video_phash, calculate_hamming
from indexer.db import SessionLocal
from models.content import Content
import shutil
import os
import tempfile
import yt_dlp
import requests

router = APIRouter()

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
        temp_path = ""
        
        if file:
            temp_path = os.path.join(temp_dir, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        elif link:
            # Logic adapted from Telegram Bot
            try:
                # Try yt-dlp first
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'outtmpl': os.path.join(temp_dir, 'temp_media.%(ext)s'),
                    'max_filesize': 50 * 1024 * 1024 # Limit 50MB
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    temp_path = ydl.prepare_filename(info)
                    
            except Exception as e:
                # Fallback to direct download
                try:
                    response = requests.get(link, stream=True)
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', '')
                    
                    ext = ""
                    if 'image' in content_type: ext = ".jpg"
                    elif 'video' in content_type: ext = ".mp4"
                    else: ext = ".bin" # Try to detect later or fail
                    
                    temp_path = os.path.join(temp_dir, f"url_content{ext}")
                    
                    with open(temp_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                except Exception as direct_e:
                    raise HTTPException(status_code=400, detail=f"Failed to process link: {str(e)} | Direct: {str(direct_e)}")

        if not os.path.exists(temp_path):
             raise HTTPException(status_code=400, detail="Could not retrieve file from input")

        # Generate pHash
        content_type = file.content_type if file else ""
        filename = file.filename if file else temp_path
        
        if "video" in str(content_type) or filename.endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")):
             p_hash = get_video_phash(temp_path)
        elif "image" in str(content_type) or filename.endswith((".jpg", ".png", ".jpeg", ".webp")):
            with open(temp_path, "rb") as f:
                p_hash = get_image_phash(f.read())
        else:
            raise HTTPException(status_code=400, detail="File type not supported for hashing. Supported: JPG, PNG, MP4, MOV.")
        
        if not p_hash:
             raise HTTPException(status_code=400, detail="Could not generate hash")

        # Linear Scan Logic (replacing indexer)
        db = SessionLocal()
        contents = db.query(Content).all()
        
        best_distance = 999
        best_match = None
        
        for content in contents:
            try:
                dist = calculate_hamming(p_hash, content.phash)
                if dist < best_distance:
                    best_distance = dist
                    best_match = content
            except Exception:
                continue # Skip invalid hashes in DB
        
        db.close()

        threshold = int(os.getenv("HAMMING_THRESHOLD", 25))
        is_verified = best_distance <= threshold
        
        if not best_match:
             return {
                "status": "UNVERIFIED",
                "pHash_input": p_hash,
                "message": "No content found in registry."
            }

        return {
            "status": "VERIFIED" if is_verified else "UNVERIFIED",
            "pHash_input": p_hash,
            "pHash_match": best_match.phash,
            "hamming_distance": int(best_distance),
            "publisher": best_match.publisher,
            "title": best_match.title,
            "description": best_match.description,
            "timestamp": best_match.timestamp,
            "txHash": best_match.txhash,
            "blocknumber": best_match.blocknumber,
            "explorer_link": f"https://sepolia-blockscout.lisk.com/tx/{best_match.txhash if best_match.txhash and best_match.txhash.startswith('0x') else '0x' + (best_match.txhash or '')}",
            "message": "Content is authentic." if is_verified else "Content is different."
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
