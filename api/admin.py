"""
Admin API Endpoints
Handles admin/owner functions like adding publishers
"""

from fastapi import APIRouter, HTTPException
from models.gasless import AddPublisherRequest, RegisterResponse
from services.gasless import verify_add_publisher_signature
from services.blockchain import SignetContract
import os

router = APIRouter()
contract = SignetContract()


@router.post("/add-publisher", response_model=RegisterResponse)
async def add_publisher(request: AddPublisherRequest):
    """
    Add a new authorized publisher via gasless transaction
    
    Only the contract owner can add publishers. The owner must sign the request
    with their wallet using EIP-712.
    
    Args:
        request: AddPublisherRequest with owner_address, publisher_address, signature
        
    Returns:
        RegisterResponse with transaction hash and status
    """
    try:
        # Verify owner address matches contract owner
        contract_owner = contract.get_owner()
        if not contract_owner:
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve contract owner address"
            )
        
        # Normalize addresses for comparison
        from web3 import Web3
        owner_checksum = Web3.to_checksum_address(request.owner_address)
        contract_owner_checksum = Web3.to_checksum_address(contract_owner)
        
        if owner_checksum.lower() != contract_owner_checksum.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Only contract owner can add publishers. Contract owner is {contract_owner}"
            )
        
        # Verify signature
        is_valid, nonce = verify_add_publisher_signature(
            owner_address=request.owner_address,
            publisher_address=request.publisher_address,
            signature=request.signature
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid signature. Please check the signature was created correctly."
            )
        
        # Check if publisher is already authorized
        is_already_authorized = contract.is_publisher_authorized(request.publisher_address)
        if is_already_authorized:
            raise HTTPException(
                status_code=400,
                detail=f"Address {request.publisher_address} is already an authorized publisher"
            )
        
        # Execute gasless transaction
        result = contract.execute_add_publisher_gasless(
            owner_address=request.owner_address,
            publisher_address=request.publisher_address,
            signature=request.signature
        )
        
        return RegisterResponse(
            success=True,
            tx_hash=result['tx_hash'],
            block_number=result['block_number'],
            message=f"Publisher {request.publisher_address} added successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add publisher: {str(e)}"
        )


@router.get("/owner")
async def get_contract_owner():
    """
    Get the contract owner address
    
    Returns:
        Contract owner address
    """
    try:
        owner = contract.get_owner()
        if not owner:
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve owner address"
            )
        return {
            "owner": owner
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get owner: {str(e)}"
        )
