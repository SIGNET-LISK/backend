import imagehash
from PIL import Image, ImageOps, ImageChops
import cv2
import os
import io
import numpy as np

def trim(im):
    """Removes uniform borders (like black bars) from the image."""
    try:
        # Convert to RGB if needed (handle RGBA, etc)
        if im.mode != 'RGB':
            im = im.convert('RGB')
        
        # Get image data
        img_array = np.array(im)
        
        # Look for borders with color close to black (threshold to be lenient)
        gray = np.mean(img_array, axis=2)  # Convert to grayscale
        
        # Find rows/cols that are not mostly black (threshold = 30)
        threshold = 30
        row_mask = np.any(gray > threshold, axis=1)
        col_mask = np.any(gray > threshold, axis=0)
        
        # Find bounds
        rows = np.where(row_mask)[0]
        cols = np.where(col_mask)[0]
        
        if len(rows) > 0 and len(cols) > 0:
            top, bottom = rows[0], rows[-1] + 1
            left, right = cols[0], cols[-1] + 1
            return im.crop((left, top, right, bottom))
    except Exception as e:
        print(f"Trim warning: {e}")
        pass
    
    return im

def get_image_phash(image_data: bytes) -> str:
    """Calculates Perceptual Hash (pHash) for image data."""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Handle EXIF Orientation FIRST before any processing
        image = ImageOps.exif_transpose(image)
        
        # Convert to RGB (handle RGBA, grayscale, etc)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Auto-crop borders (handle screenshots with black bars)
        image = trim(image)
        
        # Resize to standard size for pHash (reduce noise)
        # Use high-quality resampling for consistency
        image = image.resize((128, 128), Image.Resampling.LANCZOS) 
        
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
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Auto-crop video frames too
            image = trim(image)
            
            # Use high-quality resampling for consistency
            image = image.resize((128, 128), Image.Resampling.LANCZOS)
            h = imagehash.phash(image, hash_size=16)
            hashes.append(str(h))
        else:
            # Should not happen if video is valid, but append empty/zero hash if needed
            # For robustness, just reuse previous or fail
            raise ValueError(f"Failed to read frame at {p*100}%")

    cap.release()
    
    # Concatenate all 3 hashes
    return "".join(hashes)
