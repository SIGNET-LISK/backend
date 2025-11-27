import time
import json
import os
from web3 import Web3
from sqlalchemy.orm import Session
from indexer.db import SessionLocal, engine
from models.content import Content
from indexer.search import get_verifier
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")  # Legacy, for backward compatibility
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS", CONTRACT_ADDRESS)  # Use REGISTRY_ADDRESS, fallback to CONTRACT_ADDRESS
FORWARDER_ADDRESS = os.getenv("FORWARDER_ADDRESS")

def listen_events():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Load ABI
    abi_path = os.path.join(os.path.dirname(__file__), '../abi/SignetRegistry.json')
    with open(abi_path, 'r') as f:
        abi = json.load(f)
        
    contract = w3.eth.contract(address=w3.to_checksum_address(REGISTRY_ADDRESS), abi=abi)
    
    verifier = get_verifier()
    
    print(f"🎧 Listening for events on {REGISTRY_ADDRESS}...")
    
    # Simple polling loop
    last_block = w3.eth.block_number - 5000 # Scan back 5000 blocks to catch missed events
    
    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                print(f"Processing blocks {last_block + 1} to {current_block}...")
                
                # Use get_logs instead of create_filter for better compatibility with some RPCs
                events = contract.events.ContentRegisteredFull.get_logs(from_block=last_block + 1, to_block=current_block)
                
                for event in events:
                    handle_event(event, verifier, contract, w3)
                    
                last_block = current_block
            
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

def handle_event(event, verifier, contract, w3):
    args = event['args']
    p_hash = args['pHash']
    
    # Handle indexed string (returns keccak hash bytes). Fetch actual string from tx input.
    if isinstance(p_hash, bytes) or (isinstance(p_hash, str) and len(p_hash) == 66 and p_hash.startswith('0x')):
        try:
            tx_hash = event['transactionHash']
            tx = w3.eth.get_transaction(tx_hash)
            
            # Check if transaction is from MinimalForwarder (gasless transaction)
            if FORWARDER_ADDRESS and tx['to'] and tx['to'].lower() == w3.to_checksum_address(FORWARDER_ADDRESS).lower():
                # Transaction went through MinimalForwarder
                # Decode MinimalForwarder.execute() call first
                forwarder_abi_path = os.path.join(os.path.dirname(__file__), '../abi/MinimalForwarder.json')
                if os.path.exists(forwarder_abi_path):
                    with open(forwarder_abi_path, 'r') as f:
                        forwarder_abi = json.load(f)
                    
                    forwarder_contract = w3.eth.contract(
                        address=w3.to_checksum_address(FORWARDER_ADDRESS), 
                        abi=forwarder_abi
                    )
                    
                    # Decode the execute() call
                    func_obj, func_args = forwarder_contract.decode_function_input(tx['input'])
                    
                    # func_args should contain 'req' (ForwardRequest struct/tuple) and 'signature'
                    # ForwardRequest struct: (from, to, value, gas, nonce, data)
                    # We need to extract 'data' which contains the encoded registerContent call
                    inner_data = None
                    
                    if 'req' in func_args:
                        req = func_args['req']
                        # req could be a tuple, named tuple, or dict depending on ABI
                        if isinstance(req, (list, tuple)):
                            # Tuple format: (from, to, value, gas, nonce, data)
                            if len(req) > 5:
                                inner_data = req[5]  # data is at index 5
                        elif isinstance(req, dict):
                            # Dict format: {'from': ..., 'to': ..., 'data': ..., ...}
                            inner_data = req.get('data')
                        else:
                            # Try to access as attribute (named tuple)
                            try:
                                inner_data = req.data if hasattr(req, 'data') else None
                            except:
                                pass
                    
                    # If we found the inner data, decode it as registerContent call
                    if inner_data:
                        try:
                            func_obj_inner, func_args_inner = contract.decode_function_input(inner_data)
                            if '_pHash' in func_args_inner:
                                p_hash = func_args_inner['_pHash']
                            elif 'pHash' in func_args_inner:
                                p_hash = func_args_inner['pHash']
                        except Exception as inner_e:
                            print(f"⚠️ Failed to decode inner function call: {inner_e}")
                            import traceback
                            traceback.print_exc()
                            # If we can't decode, try to continue with the hash we have
                            pass
                    else:
                        print(f"⚠️ Could not extract data from ForwardRequest")
                else:
                    print(f"⚠️ MinimalForwarder ABI not found at {forwarder_abi_path}")
            else:
                # Direct call to SignetRegistry (legacy mode)
                func_obj, func_args = contract.decode_function_input(tx['input'])
                if '_pHash' in func_args:
                    p_hash = func_args['_pHash']
                elif 'pHash' in func_args: # Try alternative name
                    p_hash = func_args['pHash']
        except Exception as e:
            print(f"⚠️ Failed to decode tx input for pHash: {e}")
            import traceback
            traceback.print_exc()
            # Don't return early - try to use the hash from event if it's valid
            # If p_hash is still a hash (bytes32), we can't use it, so return
            if isinstance(p_hash, bytes) or (isinstance(p_hash, str) and len(p_hash) == 66 and p_hash.startswith('0x')):
                print(f"⚠️ Cannot extract pHash from transaction, skipping event")
                return

    print(f"🔔 New Content Registered: {args['title']}")
    
    db: Session = SessionLocal()
    try:
        # Check if exists
        existing = db.query(Content).filter(Content.phash == p_hash).first()
        if existing:
            print(f"⚠️ Content already indexed: {p_hash}")
            return

        new_content = Content(
            phash=p_hash,
            publisher=args['publisher'],
            title=args['title'],
            description=args['description'],
            timestamp=args['timestamp'],
            txhash=event['transactionHash'].hex(),
            blocknumber=event['blockNumber']
        )
        
        db.add(new_content)
        db.commit()
        
        # Update ANN Index
        verifier.add_item(p_hash)
        print(f"✅ Indexed & Added to ANN: {args['title']}")
        
    except Exception as e:
        print(f"❌ Error processing event: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables if not exist
    from models.content import Base
    Base.metadata.create_all(bind=engine)
    
    listen_events()
