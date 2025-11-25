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
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

def listen_events():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Load ABI
    abi_path = os.path.join(os.path.dirname(__file__), '../abi/SignetRegistry.json')
    with open(abi_path, 'r') as f:
        abi = json.load(f)
        
    contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)
    
    verifier = get_verifier()
    
    print(f"🎧 Listening for events on {CONTRACT_ADDRESS}...")
    
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
            func_obj, func_args = contract.decode_function_input(tx['input'])
            if '_pHash' in func_args:
                p_hash = func_args['_pHash']
            elif 'pHash' in func_args: # Try alternative name
                p_hash = func_args['pHash']
        except Exception as e:
            print(f"⚠️ Failed to decode tx input for pHash: {e}")
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
