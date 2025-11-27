"""
Signature Verification API Endpoints
Handles signature verification for gasless transactions before execution
"""

from fastapi import APIRouter, HTTPException
from models.gasless import VerifySignatureRequest, VerifySignatureResponse
from services.gasless import verify_eip712_signature, verify_add_publisher_signature
from services.blockchain import SignetContract

router = APIRouter()
contract = SignetContract()


@router.post("/verify-signature", response_model=VerifySignatureResponse)
async def verify_signature(request: VerifySignatureRequest):
    """
    Verify EIP-712 signature for content registration without executing transaction
    
    This endpoint allows users to verify their signature is correct before submitting
    the actual transaction. It checks:
    - Signature format is valid
    - Signature was signed by the user address
    - Nonce matches current blockchain nonce
    
    Args:
        request: VerifySignatureRequest with user_address, p_hash, title, description, signature
        
    Returns:
        VerifySignatureResponse with validation status and current nonce
    """
    try:
        # Verify user is authorized publisher
        is_authorized = contract.is_publisher_authorized(request.user_address)
        if not is_authorized:
            return VerifySignatureResponse(
                valid=False,
                message="User is not an authorized publisher",
                error=f"Address {request.user_address} must be added as authorized publisher first"
            )
        
        # Verify signature
        is_valid, nonce = verify_eip712_signature(
            user_address=request.user_address,
            p_hash=request.p_hash,
            title=request.title,
            description=request.description,
            signature=request.signature
        )
        
        if is_valid:
            return VerifySignatureResponse(
                valid=True,
                nonce=nonce,
                message="Signature is valid and ready to be submitted"
            )
        else:
            return VerifySignatureResponse(
                valid=False,
                nonce=nonce,
                error="Signature verification failed. Please check the signed data matches the request data.",
                message="Invalid signature"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Signature verification error: {str(e)}"
        )


@router.get("/nonce/{address}")
async def get_user_nonce(address: str):
    """
    Get current nonce for a user address
    
    This is useful for frontend to build the ForwardRequest with correct nonce
    
    Args:
        address: User's wallet address
        
    Returns:
        Current nonce value
    """
    try:
        from services.gasless import get_nonce
        nonce = get_nonce(address)
        return {
            "address": address,
            "nonce": nonce
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get nonce: {str(e)}"
        )
