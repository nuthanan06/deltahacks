import json
import sys
import os
import faiss
import torch
import open_clip
import numpy as np
from PIL import Image
from pathlib import Path


INDEX_PATH = "artifacts/v1/faiss.index"
META_PATH = "artifacts/v1/meta.json"

MODEL_NAME = "ViT-B-32"
PRETRAINED = "openai"  # Must match the model used to build the index
TOPK = 5


# Global variables for model and index (loaded once)
_model = None
_preprocess = None
_index = None
_meta = None
_device = None

def load_model_and_index():
    """Load CLIP model and FAISS index (singleton pattern)."""
    global _model, _preprocess, _index, _meta, _device
    
    if _model is not None:
        return _model, _preprocess, _index, _meta, _device
    
    # Force CPU on macOS to avoid segfault issues
    import platform
    if platform.system() == "Darwin":  # macOS
        _device = "cpu"
    else:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Get script directory to resolve relative paths
    script_dir = Path(__file__).parent
    
    # Resolve index and meta paths relative to script directory
    index_path = script_dir / INDEX_PATH
    meta_path = script_dir / META_PATH
    
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found at: {index_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found at: {meta_path}")

    # Load FAISS index and metadata
    print(f"Loading FAISS index from: {index_path}")
    _index = faiss.read_index(str(index_path))
    print(f"Loading metadata from: {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        _meta = json.load(f)
    print(f"Loaded {len(_meta)} products in index")

    # Load CLIP
    print("Loading CLIP model...")
    try:
        # Set threading and OpenMP to avoid macOS issues
        if platform.system() == "Darwin":
            # Fix OpenMP duplicate library issue on macOS
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            torch.set_num_threads(1)
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
        
        # Load model without device parameter first, then move manually
        print("Creating model architecture...")
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, 
            pretrained=PRETRAINED,
            require_pretrained=True
        )
        print("Model architecture created")
        
        # Move to device in separate step
        print(f"Moving model to {_device}...")
        _model = _model.to(_device)
        print("Model moved to device")
        
        # Set to eval mode
        print("Setting model to eval mode...")
        _model.eval()
        print("CLIP model loaded successfully!")
        
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return _model, _preprocess, _index, _meta, _device

@torch.no_grad()
def query_image(image_path: str, top_k: int = 1):
    """
    Query an image and return the top matching product(s).
    
    Args:
        image_path: Path to the image file
        top_k: Number of top results to return (default: 1)
    
    Returns:
        List of dicts with keys: barcode, name, brand, score
    """
    model, preprocess, index, meta, device = load_model_and_index()
    
    # Load and preprocess image
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")
    
    img = Image.open(str(img_path)).convert("RGB")
    x = preprocess(img).unsqueeze(0).to(device)

    # Compute embedding
    feat = model.encode_image(x)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    query_vec = feat.cpu().numpy().astype("float32")

    # Similarity search
    scores, ids = index.search(query_vec, top_k)

    # Format results
    results = []
    for idx, score in zip(ids[0], scores[0]):
        p = meta[idx]
        results.append({
            'barcode': p.get('barcode'),
            'name': p.get('name'),
            'brand': p.get('brand'),
            'score': float(score)
        })
    
    return results

@torch.no_grad()
def main(image_path: str):
    # Force CPU on macOS to avoid segfault issues
    import platform
    if platform.system() == "Darwin":  # macOS
        device = "cpu"
        print("Running on macOS - forcing CPU mode")
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Get script directory to resolve relative paths
    script_dir = Path(__file__).parent
    
    # Resolve index and meta paths relative to script directory
    index_path = script_dir / INDEX_PATH
    meta_path = script_dir / META_PATH
    
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found at: {index_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found at: {meta_path}")

    # Use the reusable query function
    results = query_image(image_path, top_k=TOPK)
    
    print("\nTop matches:")
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. score={result['score']:.3f} | "
            f"barcode={result['barcode']} | "
            f"name={result['name']} | "
            f"brand={result['brand']}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query.py path/to/image.jpg")
        sys.exit(1)

    main(sys.argv[1])