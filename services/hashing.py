import imagehash
from PIL import Image, ImageOps, ImageChops
import cv2
import os
import io
import numpy as np

def trim(im):
    """Removes uniform borders (like black bars) from the image."""
    try:
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)
    except Exception:
        pass # Fallback to original if trim fails
    return im

def get_image_phash(image_data: bytes) -> str:
    """Calculates Perceptual Hash (pHash) for image data."""
    try:
        image = Image.open(io.BytesIO(image_data))
        # Handle EXIF Orientation
        image = ImageOps.exif_transpose(image)
        
        # Auto-crop borders (handle screenshots with black bars)
        image = trim(image)
        
        # Resize to standard size for pHash (reduce noise)
        image = image.resize((128, 128), Image.LANCZOS) 
        # Calculate pHash with 16x16 (256 bit)
        p_hash = imagehash.phash(image, hash_size=16) 
        
        # Repeat hash 3 times to match video dimension (Start, Mid, End)
        # This allows image to be compared against video (somewhat)
        return str(p_hash) * 3
    except Exception as e:
        raise ValueError(f"Error hashing image: {e}")

def get_video_phash(filepath: str) -> str:
    """
    Calculates pHash from 3 keyframes (20%, 50%, 80%) of a video.
    Returns concatenated hash string.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise IOError(f"Failed to open video file: {filepath}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Define 3 points: 20%, 50%, 80%
    points = [0.2, 0.5, 0.8]
    hashes = []
    
    for p in points:
        frame_idx = int(frame_count * p)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret or frame is None:
            # Fallback to 0 if fail (or first frame)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            
        if ret and frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            # Auto-crop video frames too
            image = trim(image)
            image = image.resize((128, 128), Image.LANCZOS)
            h = imagehash.phash(image, hash_size=16)
            hashes.append(str(h))
        else:
            # Should not happen if video is valid, but append empty/zero hash if needed
            # For robustness, just reuse previous or fail
            raise ValueError(f"Failed to read frame at {p*100}%")

    cap.release()
    
    # Concatenate all 3 hashes
    return "".join(hashes)
