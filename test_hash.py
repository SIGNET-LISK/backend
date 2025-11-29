#!/usr/bin/env python3
"""
Test script to verify if hashing is consistent
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from services.hashing import get_image_phash, get_video_phash

# Test with a sample image
test_image_path = "test_image.jpg"
test_video_path = "test_video.mp4"

print("=" * 60)
print("HASH CONSISTENCY TEST")
print("=" * 60)

# Test 1: Hash same image twice
if os.path.exists(test_image_path):
    print(f"\n📸 Testing image: {test_image_path}")
    with open(test_image_path, "rb") as f:
        hash1 = get_image_phash(f.read())
    with open(test_image_path, "rb") as f:
        hash2 = get_image_phash(f.read())
    
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Match: {hash1 == hash2} ✅" if hash1 == hash2 else f"Match: False ❌")
else:
    print(f"\n⚠️  Test image not found: {test_image_path}")

# Test 2: Hash same video twice
if os.path.exists(test_video_path):
    print(f"\n🎬 Testing video: {test_video_path}")
    hash1 = get_video_phash(test_video_path)
    hash2 = get_video_phash(test_video_path)
    
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Match: {hash1 == hash2} ✅" if hash1 == hash2 else f"Match: False ❌")
else:
    print(f"\n⚠️  Test video not found: {test_video_path}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
