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
        
        return self.w3.to_hex(tx_hash)

    def get_content(self, p_hash: str):
        return self.contract.functions.getContentData(p_hash).call()
