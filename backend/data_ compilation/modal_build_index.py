import modal
import os
import json

app = modal.App("smartcart-build-index")

image = (
    modal.Image.debian_slim()
    .pip_install(
        "torch",
        "torchvision",
        "open_clip_torch",
        "faiss-cpu",
        "pillow",
        "numpy",
    )
)

# Volume for reading product data and images
dataset_volume = modal.Volume.from_name(
    "off-dataset-vol",
    create_if_missing=False,
)

# Volume for writing the index
index_volume = modal.Volume.from_name(
    "smartcart-index-vol",
    create_if_missing=True,
)

BATCH_SIZE = 64

@app.function(
    image=image,
    gpu="A10G",
    timeout=60 * 60,
    volumes={
        "/data": dataset_volume,
        "/outputs": index_volume,
    },
)
def build_index():
    """Read products and images from the dataset volume, embed with CLIP, and build FAISS index."""
    import torch
    import open_clip
    import numpy as np
    import faiss
    from PIL import Image
    import json
    import os
    from tqdm import tqdm

    device = "cuda"
    
    # Load CLIP model
    print("Loading CLIP model...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="openai",
    )
    model = model.to(device).eval()
    print("CLIP model loaded!")

    # Read products from the dataset volume
    DATA_DIR = "/data"
    PRODUCTS_FILE = f"{DATA_DIR}/products.jsonl"
    IMG_DIR = f"{DATA_DIR}/images"
    
    print(f"Reading products from {PRODUCTS_FILE}...")
    products = []
    if not os.path.exists(PRODUCTS_FILE):
        raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")
    
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                products.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    print(f"Loaded {len(products)} products")

    # Process products and images
    embeddings = []
    meta = []
    batch_imgs = []
    batch_meta = []
    
    processed = 0
    skipped = 0

    print("Processing images and generating embeddings...")
    for p in tqdm(products, desc="Processing products"):
        barcode = p.get("barcode")
        if not barcode:
            skipped += 1
            continue

        img_path = os.path.join(IMG_DIR, f"{barcode}.jpg")
        if not os.path.exists(img_path):
            skipped += 1
            continue

        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            skipped += 1
            continue

        batch_imgs.append(preprocess(img))
        batch_meta.append(p)

        if len(batch_imgs) >= BATCH_SIZE:
            batch = torch.stack(batch_imgs).to(device)
            with torch.no_grad():
                feats = model.encode_image(batch)
                feats = feats / feats.norm(dim=-1, keepdim=True)
            embeddings.append(feats.cpu().numpy().astype("float32"))
            meta.extend(batch_meta)
            batch_imgs, batch_meta = [], []
            processed += BATCH_SIZE

    # Flush remainder
    if batch_imgs:
        batch = torch.stack(batch_imgs).to(device)
        with torch.no_grad():
            feats = model.encode_image(batch)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        embeddings.append(feats.cpu().numpy().astype("float32"))
        meta.extend(batch_meta)
        processed += len(batch_imgs)

    if not embeddings:
        raise ValueError("No valid embeddings generated! Check that images exist in the volume.")

    X = np.vstack(embeddings)
    D = X.shape[1]
    print(f"Built embeddings: N={X.shape[0]}, D={D}")
    print(f"Processed {processed} products, skipped {skipped}")

    # Build FAISS index
    print("Building FAISS index...")
    index = faiss.IndexFlatIP(D)  # Inner product for cosine similarity (vectors are normalized)
    index.add(X)

    # Save index and metadata
    os.makedirs("/outputs", exist_ok=True)
    faiss.write_index(index, "/outputs/faiss.index")

    with open("/outputs/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print(f"✅ Saved index to /outputs/faiss.index and meta to /outputs/meta.json")
    index_volume.commit()


@app.local_entrypoint()
def main():
    """Entry point to build the index from Modal volume data."""
    print("🚀 Building CLIP embeddings and FAISS index from Modal volume...")
    build_index.remote()
    print("✅ Index building complete!")