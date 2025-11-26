import json
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

class SignetContract:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {RPC_URL}")
        
        self.contract_address = self.w3.to_checksum_address(CONTRACT_ADDRESS)
        
        # Load ABI
        abi_path = os.path.join(os.path.dirname(__file__), '../abi/SignetRegistry.json')
        if not os.path.exists(abi_path):
             raise FileNotFoundError(f"ABI file not found at {abi_path}")
             
        with open(abi_path, 'r') as f:
            self.abi = json.load(f)
            
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

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