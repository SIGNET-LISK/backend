"""
Gasless Transaction Service
Handles EIP-712 signature verification and gasless transaction helpers for EIP-2771 meta-transactions
"""

import json
import os
from typing import Dict, Tuple
from web3 import Web3
from eth_account import Account
from eth_utils import keccak
from dotenv import load_dotenv

load_dotenv()

# Load contract ABIs
def load_abi(filename: str):
    abi_path = os.path.join(os.path.dirname(__file__), f'../abi/{filename}')
    with open(abi_path, 'r') as f:
        return json.load(f)

FORWARDER_ABI = load_abi('MinimalForwarder.json')
REGISTRY_ABI = load_abi('SignetRegistry.json')

# Environment variables
RPC_URL = os.getenv("RPC_URL")
FORWARDER_ADDRESS = os.getenv("FORWARDER_ADDRESS")
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS")
CHAIN_ID = int(os.getenv("CHAIN_ID", "4202"))

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# EIP-712 Type Hash Constants
EIP712_DOMAIN_TYPEHASH = keccak(text='EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
FORWARD_REQUEST_TYPEHASH = keccak(text='ForwardRequest(address from,address to,uint256 value,uint256 gas,uint256 nonce,bytes data)')


def encode_type_hash(type_name: str, type_def: list) -> bytes:
    """Encode EIP-712 type hash"""
    fields = ','.join([t['type'] + ' ' + t['name'] for t in type_def])
    type_str = type_name + '(' + fields + ')'
    return keccak(text=type_str)


def hash_domain_data(domain: Dict) -> bytes:
    """Hash EIP-712 domain separator"""
    return keccak(
        EIP712_DOMAIN_TYPEHASH +
        keccak(text=domain['name']) +
        keccak(text=domain['version']) +
        domain['chainId'].to_bytes(32, 'big') +
        bytes.fromhex(domain['verifyingContract'][2:].zfill(64))
    )


def hash_forward_request(message: Dict) -> bytes:
    """Hash ForwardRequest struct for EIP-712"""
    return keccak(
        FORWARD_REQUEST_TYPEHASH +
        bytes.fromhex(message['from'][2:].zfill(64)) +
        bytes.fromhex(message['to'][2:].zfill(64)) +
        message['value'].to_bytes(32, 'big') +
        message['gas'].to_bytes(32, 'big') +
        message['nonce'].to_bytes(32, 'big') +
        keccak(hexstr=message['data'])
    )


def get_eip712_hash(domain: Dict, message: Dict) -> bytes:
    """Compute EIP-712 typed data hash"""
    domain_separator = hash_domain_data(domain)
    message_hash = hash_forward_request(message)
    
    return keccak(
        b'\x19\x01' +
        domain_separator +
        message_hash
    )


def get_nonce(user_address: str) -> int:
    """
    Get current nonce from MinimalForwarder contract for a user address
    
    Args:
        user_address: User's wallet address
        
    Returns:
        Current nonce value
    """
    try:
        forwarder_address = w3.to_checksum_address(FORWARDER_ADDRESS)
        user_address = w3.to_checksum_address(user_address)
        
        forwarder = w3.eth.contract(address=forwarder_address, abi=FORWARDER_ABI)
        nonce = forwarder.functions.getNonce(user_address).call()
        
        return int(nonce)
    except Exception as e:
        raise ValueError(f"Failed to get nonce: {str(e)}")


def encode_register_content(p_hash: str, title: str, description: str) -> str:
    """
    Encode registerContent function call
    
    Args:
        p_hash: Content hash (IPFS hash)
        title: Content title
        description: Content description
        
    Returns:
        Encoded function data as hex string
    """
    try:
        registry = w3.eth.contract(address=w3.to_checksum_address(REGISTRY_ADDRESS), abi=REGISTRY_ABI)
        encoded = registry.encodeABI(
            fn_name='registerContent',
            args=[p_hash, title, description]
        )
        return encoded
    except Exception as e:
        raise ValueError(f"Failed to encode registerContent: {str(e)}")


def encode_add_publisher(publisher_address: str) -> str:
    """
    Encode addPublisher function call
    
    Args:
        publisher_address: Address to add as publisher
        
    Returns:
        Encoded function data as hex string
    """
    try:
        publisher_address = w3.to_checksum_address(publisher_address)
        registry = w3.eth.contract(address=w3.to_checksum_address(REGISTRY_ADDRESS), abi=REGISTRY_ABI)
        
        # Use the correct method to encode function data
        encoded = registry.encodeABI(
            fn_name='addPublisher',
            args=[publisher_address]
        )
        return encoded
    except AttributeError:
        # Fallback: use functions method if encodeABI not available
        try:
            encoded = registry.functions.addPublisher(publisher_address)._encode_transaction_data()
            return encoded
        except Exception as e:
            raise ValueError(f"Failed to encode addPublisher: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to encode addPublisher: {str(e)}")


def estimate_gas(user_address: str, function_data: str, to_address: str) -> int:
    """
    Estimate gas needed for transaction with 20% buffer
    
    Args:
        user_address: User's wallet address
        function_data: Encoded function data
        to_address: Target contract address
        
    Returns:
        Estimated gas with 20% buffer
    """
    try:
        user_address = w3.to_checksum_address(user_address)
        to_address = w3.to_checksum_address(to_address)
        
        # Try to estimate gas
        gas_estimate = w3.eth.estimate_gas({
            'from': user_address,
            'to': to_address,
            'data': function_data
        })
        
        # Add 20% buffer
        gas_with_buffer = int(gas_estimate * 1.2)
        return gas_with_buffer
        
    except Exception as e:
        # Fallback to 300000 if estimation fails
        print(f"Gas estimation failed: {e}, using fallback")
        return 300000


def build_eip712_domain(forwarder_address: str, chain_id: int) -> Dict:
    """
    Build EIP-712 domain separator for MinimalForwarder
    
    Args:
        forwarder_address: MinimalForwarder contract address
        chain_id: Chain ID
        
    Returns:
        EIP-712 domain dictionary
    """
    return {
        'name': 'MinimalForwarder',
        'version': '1.0.0',
        'chainId': chain_id,
        'verifyingContract': forwarder_address
    }


def build_forward_request(
    user_address: str,
    to_address: str,
    data: str,
    nonce: int,
    gas: int = 300000,
    value: int = 0
) -> Dict:
    """
    Build ForwardRequest structure for EIP-712 signing
    
    Args:
        user_address: User's wallet address (from)
        to_address: Target contract address (to)
        data: Encoded function data
        nonce: Current nonce
        gas: Gas limit (default: 300000)
        value: ETH value to send (default: 0)
        
    Returns:
        ForwardRequest dictionary
    """
    return {
        'from': user_address,
        'to': to_address,
        'value': value,
        'gas': gas,
        'nonce': nonce,
        'data': data
    }


def verify_eip712_signature(
    user_address: str,
    p_hash: str,
    title: str,
    description: str,
    signature: str,
    nonce: int = None
) -> Tuple[bool, int]:
    try:
        user_address = w3.to_checksum_address(user_address)

        if nonce is None:
            nonce = get_nonce(user_address)

        function_data = encode_register_content(p_hash, title, description)
        gas = estimate_gas(user_address, function_data, REGISTRY_ADDRESS)

        forward_request = build_forward_request(
            user_address=user_address,
            to_address=REGISTRY_ADDRESS,
            data=function_data,
            nonce=nonce,
            gas=gas,
            value=0
        )

        domain = build_eip712_domain(FORWARDER_ADDRESS, CHAIN_ID)
        eip712_hash = get_eip712_hash(domain, forward_request)

        # convert signature
        if isinstance(signature, str) and signature.startswith("0x"):
            signature_bytes = bytes.fromhex(signature[2:])
        else:
            signature_bytes = signature

        recovered_address = Account.recover_hash(eip712_hash, signature=signature_bytes)

        is_valid = recovered_address.lower() == user_address.lower()
        return is_valid, nonce

    except Exception as e:
        print(f"Signature verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False, nonce if nonce is not None else 0


def verify_add_publisher_signature(
    owner_address: str,
    publisher_address: str,
    signature: str,
    nonce: int = None
) -> Tuple[bool, int]:
    try:
        owner_address = w3.to_checksum_address(owner_address)
        publisher_address = w3.to_checksum_address(publisher_address)

        if nonce is None:
            nonce = get_nonce(owner_address)

        function_data = encode_add_publisher(publisher_address)
        gas = estimate_gas(owner_address, function_data, REGISTRY_ADDRESS)

        forward_request = build_forward_request(
            user_address=owner_address,
            to_address=REGISTRY_ADDRESS,
            data=function_data,
            nonce=nonce,
            gas=gas,
            value=0
        )

        domain = build_eip712_domain(FORWARDER_ADDRESS, CHAIN_ID)
        eip712_hash = get_eip712_hash(domain, forward_request)

        from eth_account.messages import encode_defunct
        msg = encode_defunct(hexstr=eip712_hash.hex())

        if isinstance(signature, str) and signature.startswith("0x"):
            signature_bytes = bytes.fromhex(signature[2:])
        else:
            signature_bytes = signature

        recovered_address = Account.recover_message(msg, signature=signature_bytes)

        # 🔥 Debug prints
        print("========== DEBUG VERIFY ADD PUBLISHER ==========")
        print("EIP712 Hash:", eip712_hash.hex())
        print("Recovered Address:", recovered_address)
        print("Expected Address:", owner_address)
        print("Signature:", signature)
        print("Nonce:", nonce)
        print("Function Data:", function_data)
        print("ForwardRequest:", forward_request)
        print("==============================================")

        is_valid = recovered_address.lower() == owner_address.lower()
        return is_valid, nonce

    except Exception as e:
        print("Signature verification failed:", e)
        import traceback
        traceback.print_exc()
        return False, nonce if nonce is not None else 0

