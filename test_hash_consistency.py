#!/usr/bin/env python3
"""
Test hash consistency - verifying same file produces same hash
"""
from services.hashing import get_image_phash, get_video_phash
import hashlib

print("=" * 60)
print("HASH CONSISTENCY TEST")
print("=" * 60)

# Test 1: Create a simple test image
print("\n1️⃣  Creating test image...")
try:
    from PIL import Image
    img = Image.new('RGB', (640, 480), color='red')
    img.save('/tmp/test_red.jpg')
    print("✅ Test image created: /tmp/test_red.jpg")
except Exception as e:
    print(f"❌ Failed: {e}")
    exit(1)

# Test 2: Hash same image twice
print("\n2️⃣  Testing image hash consistency...")
try:
    with open('/tmp/test_red.jpg', 'rb') as f:
        data = f.read()
    
    hash1 = get_image_phash(data)
    hash2 = get_image_phash(data)
    
    print(f"Hash 1 (first 32 chars): {hash1[:32]}...")
    print(f"Hash 2 (first 32 chars): {hash2[:32]}...")
    
    if hash1 == hash2:
        print("✅ Image hash is CONSISTENT!")
    else:
        print("❌ Image hash is NOT consistent (different hashes)")
        print(f"   Full hash1: {hash1}")
        print(f"   Full hash2: {hash2}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
