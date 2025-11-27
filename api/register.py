from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from services.hashing import get_image_phash, get_video_phash
from services.blockchain import SignetContract
from services.gasless import verify_eip712_signature
import shutil
import os
import tempfile

router = APIRouter()
contract = SignetContract()

@router.post("/register-content")
async def register_content(
    file: UploadFile = File(None),
    title: str = Form(...),
    description: str = Form(...),
    publisher_address: str = Form(None),  # Address from wallet connected in frontend
    signature: Optional[str] = Form(None),  # EIP-712 signature for gasless
    p_hash: Optional[str] = Form(None)  # Pre-computed hash for gasless mode
):
    temp_dir = tempfile.mkdtemp()  # Initialize temp directory for both modes
    
    # GASLESS MODE: If signature provided, use meta-transaction
    if signature and publisher_address:
        try:
            # Validate publisher address
            from web3 import Web3
            publisher_address = Web3.to_checksum_address(publisher_address)
            
            # Check if address is authorized publisher
            is_authorized = contract.is_publisher_authorized(publisher_address)
            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=f"Address {publisher_address} is not authorized as publisher. Please contact admin to add you as publisher."
                )
            
            # If p_hash is provided, use it; otherwise generate from file
            if p_hash:
                computed_hash = p_hash
            elif file:
                temp_path = os.path.join(temp_dir, file.filename or "uploaded_file")
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # Generate pHash from file
                if file.content_type and file.content_type.startswith("video") or (file.filename and file.filename.endswith((".mp4", ".mov", ".avi"))):
                    computed_hash = get_video_phash(temp_path)
                else:
                    with open(temp_path, "rb") as f:
                        computed_hash = get_image_phash(f.read())
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either 'file' or 'p_hash' must be provided for gasless registration"
                )
            
            # Check if content already exists
            if contract.content_exists(computed_hash):
                raise HTTPException(
                    status_code=400,
                    detail="SIGNET: Hash already registered. This content has already been registered on the blockchain."
                )
            
            # Verify signature
            is_valid, nonce = verify_eip712_signature(
                user_address=publisher_address,
                p_hash=computed_hash,
                title=title,
                description=description,
                signature=signature
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid signature. Signature verification failed."
                )
            
            # Execute gasless transaction
            result = contract.execute_meta_transaction(
                user_address=publisher_address,
                p_hash=computed_hash,
                title=title,
                description=description,
                signature=signature
            )
            
            return {
                "success": True,
                "status": "SUCCESS",
                "pHash": computed_hash,
                "tx_hash": result['tx_hash'],
                "txHash": result['tx_hash'],  # Backward compatibility
                "block_number": result['block_number'],
                "message": "Content registered successfully via gasless transaction. Indexer will pick it up shortly."
            }
            
        except HTTPException:
            raise
        except ValueError as e:
            error_msg = str(e)
            if "Hash already registered" in error_msg:
                raise HTTPException(status_code=400, detail=error_msg)
            else:
                raise HTTPException(status_code=400, detail=f"Gasless transaction failed: {error_msg}")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute gasless registration: {str(e)}"
            )
    
    # LEGACY MODE: File upload with backend signing (backward compatible)
    if not file:
        raise HTTPException(
            status_code=400,
            detail="File is required for legacy registration mode"
        )
    
    try:
        # Legacy mode - validate publisher if address provided
        temp_path = os.path.join(temp_dir, file.filename or "uploaded_file")
        
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
        
        # Check if content already exists before registering
        if contract.content_exists(p_hash):
            raise HTTPException(
                status_code=400,
                detail="SIGNET: Hash already registered. This content has already been registered on the blockchain."
            )
                
        # Register on Blockchain (using relayer wallet from .env)
        try:
            tx_hash = contract.register_content(p_hash, title, description)
        except ValueError as e:
            # Handle blockchain revert errors (e.g., duplicate content)
            error_msg = str(e)
            if "Hash already registered" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Blockchain transaction failed: {error_msg}"
                )
        except Exception as e:
            # Handle other blockchain errors
            raise HTTPException(
                status_code=500,
                detail=f"Failed to register content on blockchain: {str(e)}"
            )
        
        return {
            "status": "SUCCESS",
            "pHash": p_hash,
            "txHash": tx_hash,
            "message": "Content registered successfully. Indexer will pick it up shortly."
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
