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

volume = modal.Volume.from_name(
    "smartcart-index-vol",
    create_if_missing=True
)

BATCH_SIZE = 64

@app.function(
    image=image,
    gpu="A10G",
    timeout=60 * 60,
    volumes={"/outputs": volume},
)
def build_index(products, images):
    import torch
    import open_clip
    import numpy as np
    import faiss
    from PIL import Image
    from io import BytesIO
    import json
    import os

    device = "cuda"

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="openai",
    )
    model = model.to(device).eval()

    embeddings = []
    meta = []
    batch_imgs = []
    batch_meta = []

    for p in products:
        barcode = p["barcode"]
        if barcode not in images:
            continue

        try:
            img = Image.open(BytesIO(images[barcode])).convert("RGB")
        except Exception:
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

    # Flush remainder
    if batch_imgs:
        batch = torch.stack(batch_imgs).to(device)
        with torch.no_grad():
            feats = model.encode_image(batch)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        embeddings.append(feats.cpu().numpy().astype("float32"))
        meta.extend(batch_meta)

    X = np.vstack(embeddings)
    D = X.shape[1]
    print(f"Built embeddings: N={X.shape[0]}, D={D}")

    index = faiss.IndexFlatIP(D)
    index.add(X)

    os.makedirs("/outputs", exist_ok=True)
    faiss.write_index(index, "/outputs/faiss.index")

    with open("/outputs/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print(f"Saved index to /outputs/faiss.index and meta to /outputs/meta.json")
    volume.commit()


@app.local_entrypoint()
def main():
    DATASET_DIR = "dataset"

    products = []
    with open(os.path.join(DATASET_DIR, "products.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            products.append(json.loads(line))

    images = {}
    img_dir = os.path.join(DATASET_DIR, "images")
    for p in products:
        path = os.path.join(img_dir, f"{p['barcode']}.jpg")
        if os.path.exists(path):
            with open(path, "rb") as f:
                images[p["barcode"]] = f.read()

    build_index.remote(products, images)