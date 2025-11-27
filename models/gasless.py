"""
Pydantic models for gasless transaction requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional


class RegisterContentRequest(BaseModel):
    """Request model for gasless content registration"""
    user_address: str = Field(..., description="User's wallet address")
    p_hash: str = Field(..., description="Content hash (IPFS hash)")
    title: str = Field(..., description="Content title")
    description: str = Field(..., description="Content description")
    signature: str = Field(..., description="EIP-712 signature from user")


class VerifySignatureRequest(BaseModel):
    """Request model for signature verification"""
    user_address: str = Field(..., description="User's wallet address")
    p_hash: str = Field(..., description="Content hash (IPFS hash)")
    title: str = Field(..., description="Content title")
    description: str = Field(..., description="Content description")
    signature: str = Field(..., description="EIP-712 signature to verify")


class ContentResponse(BaseModel):
    """Response model for content data"""
    p_hash: str = Field(..., description="Content hash")
    publisher: str = Field(..., description="Publisher wallet address")
    title: str = Field(..., description="Content title")
    description: str = Field(..., description="Content description")
    timestamp: int = Field(..., description="Registration timestamp")


class RegisterResponse(BaseModel):
    """Response model for successful registration"""
    success: bool = Field(..., description="Registration status")
    tx_hash: str = Field(..., description="Transaction hash")
    block_number: int = Field(..., description="Block number")
    p_hash: Optional[str] = Field(None, description="Content hash")
    message: str = Field(..., description="Status message")


class AddPublisherRequest(BaseModel):
    """Request model for adding publisher"""
    owner_address: str = Field(..., description="Owner's wallet address")
    publisher_address: str = Field(..., description="Address to add as publisher")
    signature: str = Field(..., description="EIP-712 signature from owner")


class VerifySignatureResponse(BaseModel):
    """Response model for signature verification"""
    valid: bool = Field(..., description="Signature validity")
    nonce: Optional[int] = Field(None, description="Current nonce used for verification")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if invalid")


class PublisherStatusResponse(BaseModel):
    """Response model for publisher status check"""
    address: str = Field(..., description="Publisher address")
    is_authorized: bool = Field(..., description="Authorization status")


class ContentsListResponse(BaseModel):
    """Response model for contents list"""
    contents: list[ContentResponse] = Field(..., description="List of contents")
    total: int = Field(..., description="Total number of contents")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")
