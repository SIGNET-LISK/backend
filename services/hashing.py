import imagehash
from PIL import Image
import cv2
import os
import io
import numpy as np

# --- 1. CORE LOGIC: HASHING ---

def get_image_phash(image_data: bytes) -> str:
    """Menghitung Perceptual Hash (pHash) untuk file gambar."""
    image = Image.open(io.BytesIO(image_data))
    # Resize ke ukuran standar untuk pHash (mengurangi noise)
    image = image.resize((128, 128), Image.LANCZOS) 
    # Hitung pHash dengan 8x8 (64 bit) atau 16x16 (256 bit)
    p_hash = imagehash.phash(image, hash_size=16) 
    return str(p_hash)

def get_video_phash(filepath: str) -> str:
    """
    Menghitung pHash dari FRAME TENGAH video (lebih stabil terhadap padding/trimming).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File video tidak ditemukan: {filepath}")

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise IOError(f"Gagal membuka file video: {filepath}")

    # 1. Dapatkan Total Jumlah Frame
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 2. Hitung Index Frame Tengah (mid-frame)
    if frame_count < 20: # Jika video terlalu pendek
        frame_to_hash = 0
    else:
        frame_to_hash = frame_count // 2 # Bagi dua (tengah)
    
    # Set frame position ke frame tengah
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_hash)
    
    ret, frame = cap.read()
    cap.release() 

    if not ret or frame is None:
        raise ValueError(f"Gagal membaca frame ke-{frame_to_hash} dari video.")
    
    # Konversi dan Hash
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    
    p_hash = imagehash.phash(image, hash_size=16)
    return str(p_hash)


# --- 2. CORE LOGIC: HAMMING DISTANCE ---

def calculate_hamming(hash_a: str, hash_b: str) -> int:
    """Menghitung Hamming Distance (jumlah perbedaan bit) antara dua string hash."""
    try:
        # Konversi string hash heksadesimal ke objek ImageHash
        hash_obj_a = imagehash.hex_to_hash(hash_a)
        hash_obj_b = imagehash.hex_to_hash(hash_b)
        
        # Perhitungan dilakukan secara otomatis oleh library ImageHash
        return hash_obj_a - hash_obj_b
    except ValueError:
        raise ValueError("Hash harus berupa string heksadesimal yang valid.")
