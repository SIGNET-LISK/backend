import imagehash
import hnswlib
import numpy as np
import os
import pickle

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
        self.p = hnswlib.Index(space='l2', dim=DIMENSION) # Using L2 as proxy for Hamming? Or use custom?
        # Hnswlib doesn't support hamming directly efficiently in python bindings usually, 
        # but L2 on binary vectors is related to Hamming. 
        # Better: use 'cosine' or just L2. For binary vectors, L2^2 = Hamming distance.
        
        self.metadata_path = index_path.replace('.bin', '.pkl')
        
        self.last_mod_time = 0
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path):
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
        else:
            self.p.init_index(max_elements=MAX_ELEMENTS, ef_construction=EF_CONSTRUCTION, M=M)
            self.p.set_ef(EF_SEARCH)
            self.hashes = {}
            self.current_id = 0
            self.last_mod_time = 0

    def add_item(self, p_hash: str):
        # Convert hex hash to binary vector
        vector = self._phash_to_vector(p_hash)
        
        # Check if already exists (naive check for now, or rely on ID mapping)
        # In a real system we might want to avoid duplicates or handle them.
        
        self.p.add_items(vector, np.array([self.current_id]))
        self.hashes[self.current_id] = p_hash
        self.current_id += 1
        
        # Save index and metadata
        self.p.save_index(self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump({'hashes': self.hashes, 'current_id': self.current_id}, f)
        
        self.last_mod_time = os.path.getmtime(self.index_path)

    def search(self, p_hash: str, k: int = 1):
        # Check if index file has changed (reloaded by another process)
        if os.path.exists(self.index_path):
            mod_time = os.path.getmtime(self.index_path)
            if mod_time > self.last_mod_time:
                print("🔄 Index changed on disk, reloading...")
                self._load_index()

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
                # Calculate exact hamming distance to be sure
                dist = self.hamming_distance(p_hash, stored_phash)
                results.append((stored_phash, dist))
        
        return results

    def _phash_to_vector(self, p_hash: str) -> np.ndarray:
        """Converts hex pHash string (potentially concatenated) to numpy float array."""
        # Check if it's a composite hash (length 64 hex chars * 3 = 192 chars)
        # Standard 256-bit hash is 64 hex chars.
        
        chunk_size = 64 # 256 bits / 4 bits per hex = 64 chars
        vectors = []
        
        # Pad if short (should not happen with new logic, but for safety)
        if len(p_hash) < chunk_size * 3:
             # If single hash, repeat it 3 times
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
