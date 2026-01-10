import json
import sys
import faiss
import torch
import open_clip
import numpy as np
from PIL import Image


INDEX_PATH = "artifacts/v0-test/faiss.index"
META_PATH = "artifacts/v0-test/meta.json"

MODEL_NAME = "ViT-B-32"
PRETRAINED = "openai"
TOPK = 5


@torch.no_grad()
def main(image_path: str):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load FAISS index and metadata
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Load CLIP
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED
    )
    model = model.to(device).eval()

    # Load and preprocess image
    img = Image.open(image_path).convert("RGB")
    x = preprocess(img).unsqueeze(0).to(device)

    # Compute embedding
    feat = model.encode_image(x)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    query_vec = feat.cpu().numpy().astype("float32")

    # Similarity search
    scores, ids = index.search(query_vec, TOPK)

    print("\nTop matches:")
    for rank, (idx, score) in enumerate(zip(ids[0], scores[0]), start=1):
        p = meta[idx]
        print(
            f"{rank}. score={score:.3f} | "
            f"barcode={p.get('barcode')} | "
            f"name={p.get('name')} | "
            f"brand={p.get('brand')}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query.py path/to/image.jpg")
        sys.exit(1)

    main(sys.argv[1])