from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.hashing import get_image_phash, get_video_phash
from indexer.search import get_verifier
from indexer.db import SessionLocal
from models.content import Content
import shutil
import os
import tempfile
import yt_dlp
import requests
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
verifier = get_verifier()

@router.post("/verify")
async def verify_content(
    file: UploadFile = File(None),
    link: str = Form(None)
):
    logger.info(f"🔍 Verify request: file={file.filename if file else None}, link={link}")
    
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
        logger.info(f"📊 Generating hash for file: {temp_path}")
        try:
            if temp_path.endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")) or "video" in str(file.content_type if file else ""):
                 logger.info("🎬 Detecting as video")
                 p_hash = get_video_phash(temp_path)
            else:
                logger.info("🖼️  Detecting as image")
                with open(temp_path, "rb") as f:
                    p_hash = get_image_phash(f.read())
            logger.info(f"✅ Hash generated: {p_hash[:16]}...")
        except Exception as hash_e:
            logger.error(f"❌ Hash generation failed: {hash_e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Hash generation failed: {str(hash_e)}")
        
        if not p_hash:
             raise HTTPException(status_code=400, detail="Could not generate hash")

        # Search in ANN
        logger.info(f"🔎 Searching in index with hash: {p_hash[:16]}...")
        try:
            matches = verifier.search(p_hash, k=1)
            logger.info(f"📈 Search results: {len(matches)} matches found")
        except Exception as search_e:
            logger.error(f"❌ Search failed: {search_e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Search failed: {str(search_e)}")
        
        if not matches:
            logger.info("⚠️  No matches found")
            return {
                "status": "UNVERIFIED",
                "pHash": p_hash,
                "pHash_input": p_hash,
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
                "pHash_input": p_hash,  # Add for consistency
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
            "description": content.description,
            "timestamp": content.timestamp,
            "txHash": content.txhash,
            "blocknumber": content.blocknumber,
            "explorer_link": f"https://sepolia-blockscout.lisk.com/tx/{content.txhash if content.txhash.startswith('0x') else '0x' + content.txhash}",
            "message": "Content is authentic." if is_verified else "Content is different."
        }

    except HTTPException as he:
        logger.warning(f"⚠️  HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ Unexpected error in verify: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
