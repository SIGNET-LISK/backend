import json
import os
from typing import Dict, List
from web3 import Web3
from dotenv import load_dotenv
from services.gasless import (
    get_nonce,
    encode_register_content,
    encode_add_publisher,
    estimate_gas,
    build_forward_request
)

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS", CONTRACT_ADDRESS)
FORWARDER_ADDRESS = os.getenv("FORWARDER_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY", PRIVATE_KEY)

class SignetContract:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {RPC_URL}")
        
        self.contract_address = self.w3.to_checksum_address(REGISTRY_ADDRESS)
        
        # Load SignetRegistry ABI
        abi_path = os.path.join(os.path.dirname(__file__), '../abi/SignetRegistry.json')
        if not os.path.exists(abi_path):
             raise FileNotFoundError(f"ABI file not found at {abi_path}")
             
        with open(abi_path, 'r') as f:
            self.abi = json.load(f)
            
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        
        # Load MinimalForwarder ABI and contract
        self.forwarder_address = None
        self.forwarder_contract = None
        if FORWARDER_ADDRESS:
            try:
                self.forwarder_address = self.w3.to_checksum_address(FORWARDER_ADDRESS)
                forwarder_abi_path = os.path.join(os.path.dirname(__file__), '../abi/MinimalForwarder.json')
                with open(forwarder_abi_path, 'r') as f:
                    forwarder_abi = json.load(f)
                self.forwarder_contract = self.w3.eth.contract(address=self.forwarder_address, abi=forwarder_abi)
            except Exception as e:
                print(f"Warning: Could not load forwarder contract: {e}")

    def register_content(self, p_hash: str, title: str, description: str) -> str:
        if not PRIVATE_KEY:
            raise ValueError("PRIVATE_KEY not set in environment variables")
            
        account = self.w3.eth.account.from_key(PRIVATE_KEY)
        
        # Build transaction
        tx = self.contract.functions.registerContent(
            p_hash,
            title,
            description
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send
        signed_tx = self.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for transaction receipt and check for revert
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        # Check if transaction reverted
        if receipt['status'] == 0:
            # Transaction reverted, try to get revert reason by simulating the call
            try:
                # Simulate the call to get the revert reason
                self.contract.functions.registerContent(
                    p_hash,
                    title,
                    description
                ).call({'from': account.address})
                # If call succeeds, this shouldn't happen, but provide generic error
                raise ValueError("Transaction reverted for unknown reason")
            except Exception as e:
                error_msg = str(e)
                # Extract meaningful error message from the exception
                if "Hash already registered" in error_msg or "SIGNET: Hash already registered" in error_msg:
                    raise ValueError("SIGNET: Hash already registered. This content has already been registered on the blockchain.")
                elif "Not an authorized publisher" in error_msg or "SIGNET: Not an authorized publisher" in error_msg:
                    raise ValueError("SIGNET: Not an authorized publisher.")
                elif "Content not found" in error_msg:
                    # This shouldn't happen during registration, but handle it
                    raise ValueError("SIGNET: Content not found.")
                else:
                    # Generic revert error - could be duplicate or other issue
                    raise ValueError(f"Transaction reverted: {error_msg}")
        
        return self.w3.to_hex(tx_hash)

    def get_content(self, p_hash: str):
        return self.contract.functions.getContentData(p_hash).call()
    
    def content_exists(self, p_hash: str) -> bool:
        """Check if content with given hash already exists in the registry"""
        try:
            # Try to get content data - if it succeeds, content exists
            # getContentData will revert if content not found, so we catch that
            publisher, _, _, _ = self.contract.functions.getContentData(p_hash).call()
            # If we get here, content exists (publisher is not zero address)
            return publisher != "0x0000000000000000000000000000000000000000"
        except Exception:
            # If call fails (content not found), content doesn't exist
            return False
    
    def is_publisher_authorized(self, address: str) -> bool:
        """Check if an address is authorized as publisher"""
        try:
            return self.contract.functions.authorizedPublishers(address).call()
        except Exception as e:
            return False
    
    def get_owner(self) -> str:
        """Get contract owner address"""
        try:
            return self.contract.functions.owner().call()
        except Exception as e:
            return ""
    
    def execute_meta_transaction(
        self,
        user_address: str,
        p_hash: str,
        title: str,
        description: str,
        signature: str
    ) -> Dict[str, any]:
        """
        Execute gasless content registration via MinimalForwarder
        
        Args:
            user_address: User's wallet address
            p_hash: Content hash
            title: Content title
            description: Content description
            signature: User's EIP-712 signature
            
        Returns:
            Dictionary with tx_hash and block_number
        """
        if not RELAYER_PRIVATE_KEY:
            raise ValueError("RELAYER_PRIVATE_KEY not set in environment variables")
        
        if not self.forwarder_contract:
            raise ValueError("MinimalForwarder contract not initialized. Check FORWARDER_ADDRESS.")
        
        try:
            # Normalize addresses
            user_address = self.w3.to_checksum_address(user_address)
            
            # Get relayer account
            relayer_account = self.w3.eth.account.from_key(RELAYER_PRIVATE_KEY)
            
            # Get nonce
            nonce = get_nonce(user_address)
            
            # Encode function data
            function_data = encode_register_content(p_hash, title, description)
            
            # Use the same gas as frontend (300000) for ForwardRequest
            # IMPORTANT: This must match the gas value used when signing
            gas = 300000
            
            # Build ForwardRequest
            forward_request = build_forward_request(
                user_address=user_address,
                to_address=REGISTRY_ADDRESS,
                data=function_data,
                nonce=nonce,
                gas=gas,
                value=0
            )
            
            # Convert ForwardRequest to tuple format for contract call
            request_tuple = (
                forward_request['from'],
                forward_request['to'],
                forward_request['value'],
                forward_request['gas'],
                forward_request['nonce'],
                forward_request['data']
            )
            
            # Build transaction for forwarder.execute()
            tx = self.forwarder_contract.functions.execute(
                request_tuple,
                signature
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': self.w3.eth.get_transaction_count(relayer_account.address),
                'gas': gas + 50000,  # Add buffer for forwarder overhead
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, RELAYER_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Check if transaction reverted
            if receipt['status'] == 0:
                raise ValueError("Meta-transaction execution reverted")
            
            return {
                'tx_hash': self.w3.to_hex(tx_hash),
                'block_number': receipt['blockNumber']
            }
            
        except Exception as e:
            raise ValueError(f"Failed to execute meta-transaction: {str(e)}")
    
    def execute_add_publisher_gasless(
        self,
        owner_address: str,
        publisher_address: str,
        signature: str
    ) -> Dict[str, any]:
        """
        Execute gasless addPublisher via MinimalForwarder
        
        Args:
            owner_address: Owner's wallet address
            publisher_address: Address to add as publisher
            signature: Owner's EIP-712 signature
            
        Returns:
            Dictionary with tx_hash and block_number
        """
        if not RELAYER_PRIVATE_KEY:
            raise ValueError("RELAYER_PRIVATE_KEY not set in environment variables")
        
        if not self.forwarder_contract:
            raise ValueError("MinimalForwarder contract not initialized")
        
        try:
            # Normalize addresses
            owner_address = self.w3.to_checksum_address(owner_address)
            publisher_address = self.w3.to_checksum_address(publisher_address)
            
            # Get relayer account
            relayer_account = self.w3.eth.account.from_key(RELAYER_PRIVATE_KEY)
            
            # Get nonce
            nonce = get_nonce(owner_address)
            
            # Encode function data
            function_data = encode_add_publisher(publisher_address)
            
            # Use the same gas as frontend (300000) for ForwardRequest
            # IMPORTANT: This must match the gas value used when signing
            gas = 300000
            
            # Build ForwardRequest
            forward_request = build_forward_request(
                user_address=owner_address,
                to_address=REGISTRY_ADDRESS,
                data=function_data,
                nonce=nonce,
                gas=gas,
                value=0
            )
            
            # Convert ForwardRequest to tuple format
            request_tuple = (
                forward_request['from'],
                forward_request['to'],
                forward_request['value'],
                forward_request['gas'],
                forward_request['nonce'],
                forward_request['data']
            )
            
            # Build transaction for forwarder.execute()
            tx = self.forwarder_contract.functions.execute(
                request_tuple,
                signature
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': self.w3.eth.get_transaction_count(relayer_account.address),
                'gas': gas + 50000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, RELAYER_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Check if transaction reverted
            if receipt['status'] == 0:
                raise ValueError("Meta-transaction execution reverted")
            
            return {
                'tx_hash': self.w3.to_hex(tx_hash),
                'block_number': receipt['blockNumber']
            }
            
        except Exception as e:
            raise ValueError(f"Failed to execute add publisher: {str(e)}")
    
    def get_all_hashes(self, limit: int = 50, offset: int = 0) -> List[str]:
        """
        Get all registered content hashes with pagination
        
        Args:
            limit: Maximum number of hashes to return
            offset: Number of hashes to skip
            
        Returns:
            List of content hashes
        """
        try:
            all_hashes = self.contract.functions.getAllHashes().call()
            return all_hashes[offset:offset + limit]
        except Exception as e:
            raise ValueError(f"Failed to get hashes: {str(e)}")
    
    def get_content_detailed(self, p_hash: str) -> Dict[str, any]:
        """
        Get detailed content information
        
        Args:
            p_hash: Content hash
            
        Returns:
            Dictionary with content details
        """
        try:
            publisher, title, description, timestamp = self.contract.functions.getContentData(p_hash).call()
            return {
                'p_hash': p_hash,
                'publisher': publisher,
                'title': title,
                'description': description,
                'timestamp': int(timestamp)
            }
        except Exception as e:
            raise ValueError(f"Content not found: {str(e)}")