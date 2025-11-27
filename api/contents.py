"""
Contents Query API Endpoints
Handles querying registered contents with filtering and pagination
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from indexer.db import get_db
from models.content import Content
from models.gasless import ContentResponse, PublisherStatusResponse
from services.blockchain import SignetContract

router = APIRouter()
contract = SignetContract()


@router.get("/contents")
def get_contents(
    publisher: Optional[str] = Query(None, description="Filter by publisher address"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Get list of registered contents with optional filtering and pagination
    
    Args:
        publisher: Optional filter by publisher address
        limit: Maximum number of results (1-100, default: 50)
        offset: Number of results to skip (default: 0)
        db: Database session
        
    Returns:
        List of contents with pagination info
    """
    try:
        # Build query
        query = db.query(Content).order_by(Content.created_at.desc())
        
        # Apply publisher filter if provided
        if publisher:
            from web3 import Web3
            publisher_checksum = Web3.to_checksum_address(publisher)
            query = query.filter(Content.publisher == publisher_checksum)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        contents = query.limit(limit).offset(offset).all()
        
        return {
            "contents": contents,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch contents: {str(e)}"
        )


@router.get("/contents/{p_hash}", response_model=ContentResponse)
def get_content_by_hash(p_hash: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific content by hash
    
    Args:
        p_hash: Content hash (IPFS hash)
        db: Database session
        
    Returns:
        Content details
    """
    try:
        # Try from database first (faster)
        content = db.query(Content).filter(Content.phash == p_hash).first()
        
        if content:
            return ContentResponse(
                p_hash=content.phash,
                publisher=content.publisher,
                title=content.title,
                description=content.description,
                timestamp=content.timestamp
            )
        
        # If not in DB, try blockchain
        try:
            content_data = contract.get_content_detailed(p_hash)
            return ContentResponse(**content_data)
        except:
            raise HTTPException(
                status_code=404,
                detail=f"Content with hash {p_hash} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch content: {str(e)}"
        )


@router.get("/publisher/{address}", response_model=PublisherStatusResponse)
def check_publisher_status(address: str):
    """
    Check if an address is an authorized publisher
    
    Args:
        address: Wallet address to check
        
    Returns:
        Publisher authorization status
    """
    try:
        from web3 import Web3
        address_checksum = Web3.to_checksum_address(address)
        
        is_authorized = contract.is_publisher_authorized(address_checksum)
        
        return PublisherStatusResponse(
            address=address_checksum,
            is_authorized=is_authorized
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check publisher status: {str(e)}"
        )

