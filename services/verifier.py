import imagehash
import hnswlib
import numpy as np
import os
import pickle
import json
from indexer.db import SessionLocal
from models.content import Content

# Constants
HASH_SIZE = 16
HASH_LENGTH = HASH_SIZE * HASH_SIZE # 256 bits
DIMENSION = HASH_LENGTH * 3 # 3 Frames for Video (Start, Mid, End) 
MAX_ELEMENTS = 10000
M = 16
EF_CONSTRUCTION = 200
EF_SEARCH = 50

class ANNVerifier:
    def __init__(self, index_path='index.bin'):
        self.index_path = index_path
        self.p = hnswlib.Index(space='l2', dim=DIMENSION)
        self.metadata_path = index_path.replace('.bin', '.pkl')
        
        self.last_mod_time = 0
        self._load_index()

    def _load_index(self):
        """Load index from database (primary) or file (fallback)"""
        try:
            # Try loading from database first
            self._load_from_db()
            print("✅ Index loaded from database")
        except Exception as e:
            print(f"⚠️  Failed to load from database: {e}, falling back to file")
            # Fallback to file
            if os.path.exists(self.index_path):
                try:
                    self.p.load_index(self.index_path)
                    self.last_mod_time = os.path.getmtime(self.index_path)
                    if os.path.exists(self.metadata_path):
                        with open(self.metadata_path, 'rb') as f:
                            data = pickle.load(f)
                            self.hashes = data.get('hashes', {})
                            self.current_id = data.get('current_id', 0)
                    else:
                        self.hashes = {}
                        self.current_id = 0
                    print("✅ Index loaded from file")
                except Exception as file_e:
                    print(f"⚠️  Failed to load from file: {file_e}, starting fresh")
                    self._init_fresh()
            else:
                self._init_fresh()

    def _init_fresh(self):
        """Initialize fresh index"""
        self.p.init_index(max_elements=MAX_ELEMENTS, ef_construction=EF_CONSTRUCTION, M=M)
        self.p.set_ef(EF_SEARCH)
        self.hashes = {}
        self.current_id = 0
        self.last_mod_time = 0
        print("✅ Index initialized fresh")

    def _load_from_db(self):
        """Load all content from database and populate index"""
        db = SessionLocal()
        try:
            contents = db.query(Content).all()
            
            if not contents:
                self._init_fresh()
                return
            
            # Initialize index
            self.p.init_index(max_elements=MAX_ELEMENTS, ef_construction=EF_CONSTRUCTION, M=M)
            self.p.set_ef(EF_SEARCH)
            self.hashes = {}
            self.current_id = 0
            
            # Load all content
            for content in contents:
                vector = self._phash_to_vector(content.phash)
                self.p.add_items(vector, np.array([self.current_id]))
                self.hashes[self.current_id] = content.phash
                self.current_id += 1
            
            print(f"✅ Loaded {len(contents)} items from database into index")
            
        finally:
            db.close()

    def add_item(self, p_hash: str):
        """Add item to index (in-memory only, DB is authoritative source)"""
        # Convert hex hash to binary vector
        vector = self._phash_to_vector(p_hash)
        
        self.p.add_items(vector, np.array([self.current_id]))
        self.hashes[self.current_id] = p_hash
        self.current_id += 1
        
        # Save backup to file (for persistence if DB fails)
        try:
            self.p.save_index(self.index_path)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({'hashes': self.hashes, 'current_id': self.current_id}, f)
        except Exception as e:
            print(f"⚠️  Warning: Could not save index backup to file: {e}")

    def search(self, p_hash: str, k: int = 1):
        """Search for similar hash in index"""
        # Check if we need to reload from DB (in case data changed in DB)
        # This is for multi-process safety
        try:
            db = SessionLocal()
            db_count = db.query(Content).count()
            db.close()
            
            if db_count != len(self.hashes):
                print(f"🔄 Reloading index from DB (count mismatch: {len(self.hashes)} vs {db_count})")
                self._load_from_db()
        except Exception as e:
            print(f"⚠️  Could not check DB count: {e}")

        if self.p.element_count == 0:
            return []
            
        vector = self._phash_to_vector(p_hash)
        
        # Safety check for k
        current_count = self.p.element_count
        k = min(k, current_count)
        
        labels, distances = self.p.knn_query(vector, k=k)
        
        results = []
        for i, label in enumerate(labels[0]):
            stored_phash = self.hashes.get(label)
            if stored_phash:
                # Calculate exact hamming distance
                dist = self.hamming_distance(p_hash, stored_phash)
                results.append((stored_phash, dist))
        
        return results

    def _phash_to_vector(self, p_hash: str) -> np.ndarray:
        """Converts hex pHash string to numpy float array"""
        chunk_size = 64
        vectors = []
        
        # Pad if short
        if len(p_hash) < chunk_size * 3:
             p_hash = p_hash * 3
             
        # Take first 3 chunks
        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size
            chunk = p_hash[start:end]
            if len(chunk) < chunk_size:
                chunk = chunk.ljust(chunk_size, '0')
                
            hash_obj = imagehash.hex_to_hash(chunk)
            vectors.append(hash_obj.hash.flatten().astype(np.float32))
            
        return np.concatenate(vectors)

    @staticmethod
    def hamming_distance(hash_a: str, hash_b: str) -> int:
        chunk_size = 64
        total_dist = 0
        
        # Normalize lengths
        if len(hash_a) < chunk_size * 3: hash_a = hash_a * 3
        if len(hash_b) < chunk_size * 3: hash_b = hash_b * 3
        
        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size
            
            chunk_a = hash_a[start:end]
            chunk_b = hash_b[start:end]
            
            try:
                hash_obj_a = imagehash.hex_to_hash(chunk_a)
                hash_obj_b = imagehash.hex_to_hash(chunk_b)
                total_dist += (hash_obj_a - hash_obj_b)
            except:
                pass # Ignore invalid chunks
                
        return total_dist
