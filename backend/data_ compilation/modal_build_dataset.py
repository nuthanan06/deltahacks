import modal

app = modal.App("off-dataset-builder")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "requests",
        "tqdm",
        "pillow",
        "certifi",
    )
)

volume = modal.Volume.from_name(
    "off-dataset-vol",
    create_if_missing=False,
)

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"
HEADERS = {
    "User-Agent": "SmartCart/1.0 (student project)"
}

PAGE_SIZE = 50
MAX_PAGES = 200          # effectively unlimited
SLEEP = 0.03
NUM_WORKERS = 16           # Number of parallel workers

@app.function(
    image=image,
    cpu=2,          # Per worker
    memory=4096,    # Per worker
    timeout=60 * 60 * 6,
    volumes={"/data": volume},
)
def build_dataset_worker(worker_id: int, start_page: int, end_page: int):
    """Process a range of pages in parallel with other workers."""
    import os
    import json
    import time
    import requests
    from tqdm import tqdm

    DATA_DIR = "/data"
    IMG_DIR = f"{DATA_DIR}/images"
    META_FILE = f"{DATA_DIR}/products.jsonl"
    WORKER_FILE = f"{DATA_DIR}/products_worker_{worker_id}.jsonl"
    PROGRESS_FILE = f"{DATA_DIR}/progress_worker_{worker_id}.txt"

    os.makedirs(IMG_DIR, exist_ok=True)

    # -------------------------
    # Load seen barcodes from main file (if exists)
    # -------------------------
    seen = set()
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["barcode"])
                except:
                    pass

    # Also check other worker files that might have been written
    for w_id in range(NUM_WORKERS):
        worker_file = f"{DATA_DIR}/products_worker_{w_id}.jsonl"
        if os.path.exists(worker_file) and w_id != worker_id:
            with open(worker_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        seen.add(json.loads(line)["barcode"])
                    except:
                        pass

    def search_page(page):
        params = {
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": PAGE_SIZE,
            "page": page,
            "tagtype_0": "states",
            "tag_contains_0": "contains",
            "tag_0": "en:complete",
        }
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json().get("products", [])

    def download(url, path):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and r.content:
                with open(path, "wb") as f:
                    f.write(r.content)
                return True
        except:
            return False
        return False

    # -------------------------
    # Main loop for this worker's page range
    # -------------------------
    page = start_page
    processed = 0
    
    while page <= end_page:
        print(f"\n[Worker {worker_id}] 📦 Fetching page {page}")
        products = search_page(page)
        if not products:
            break

        with open(WORKER_FILE, "a", encoding="utf-8") as meta_out:
            for p in tqdm(products, desc=f"Worker {worker_id} - Page {page}"):
                barcode = p.get("code")
                name = p.get("product_name") or p.get("product_name_en")
                brand = p.get("brands")
                categories = p.get("categories")
                img_url = p.get("image_front_url")

                if not barcode or not name or not img_url:
                    continue
                if barcode in seen:
                    continue

                img_path = f"{IMG_DIR}/{barcode}.jpg"
                # Check if image already exists (might have been downloaded by another worker)
                if os.path.exists(img_path):
                    seen.add(barcode)
                    continue

                ok = download(img_url, img_path)
                if not ok:
                    continue

                record = {
                    "barcode": barcode,
                    "name": name,
                    "brand": brand,
                    "categories": categories,
                    "image_path": img_path,
                }

                meta_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                seen.add(barcode)
                processed += 1
                time.sleep(SLEEP)

        with open(PROGRESS_FILE, "w") as f:
            f.write(str(page))

        volume.commit()
        page += 1

    print(f"\n[Worker {worker_id}] ✅ Completed pages {start_page}-{end_page}, processed {processed} products")
    return {"worker_id": worker_id, "pages_processed": end_page - start_page + 1, "products": processed}


@app.function(
    image=image,
    cpu=2,
    memory=4096,
    timeout=60 * 60,
    volumes={"/data": volume},
)
def merge_worker_files():
    """Merge all worker files into the main products.jsonl file."""
    import os
    import json
    from collections import defaultdict

    DATA_DIR = "/data"
    META_FILE = f"{DATA_DIR}/products.jsonl"
    
    # Load existing products to avoid duplicates
    existing_barcodes = set()
    existing_products = []
    
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    barcode = record.get("barcode")
                    if barcode:
                        existing_barcodes.add(barcode)
                        existing_products.append(record)
                except:
                    pass

    # Collect all products from worker files
    all_products = []
    seen_barcodes = set(existing_barcodes)
    
    for worker_id in range(NUM_WORKERS):
        worker_file = f"{DATA_DIR}/products_worker_{worker_id}.jsonl"
        if os.path.exists(worker_file):
            print(f"Merging {worker_file}...")
            with open(worker_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        barcode = record.get("barcode")
                        if barcode and barcode not in seen_barcodes:
                            all_products.append(record)
                            seen_barcodes.add(barcode)
                    except:
                        pass

    # Write merged file
    print(f"Writing {len(existing_products) + len(all_products)} total products to {META_FILE}")
    with open(META_FILE, "w", encoding="utf-8") as f:
        for record in existing_products:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        for record in all_products:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    volume.commit()
    return {"total_products": len(existing_products) + len(all_products), "new_products": len(all_products)}


@app.local_entrypoint()
def main(num_workers: int = NUM_WORKERS):
    """
    Run parallel dataset building.
    
    Args:
        num_workers: Number of parallel workers to spawn (default: 8)
    """
    # Calculate page ranges for each worker
    pages_per_worker = MAX_PAGES // num_workers
    page_ranges = []
    
    for i in range(num_workers):
        start = i * pages_per_worker + 1
        end = (i + 1) * pages_per_worker if i < num_workers - 1 else MAX_PAGES
        page_ranges.append((start, end))
    
    print(f"🚀 Launching {num_workers} workers:")
    for i, (start, end) in enumerate(page_ranges):
        print(f"  Worker {i}: pages {start}-{end}")
    
    # Launch all workers in parallel
    futures = [
        build_dataset_worker.spawn(i, start, end)
        for i, (start, end) in enumerate(page_ranges)
    ]
    
    # Wait for all workers to complete
    results = [f.get() for f in futures]
    
    print("\n✅ All workers completed!")
    for result in results:
        print(f"  Worker {result['worker_id']}: {result['products']} products from {result['pages_processed']} pages")
    
    # Merge all worker files
    print("\n🔄 Merging worker files...")
    merge_result = merge_worker_files.remote()
    print(f"✅ Merge complete: {merge_result}")


@app.local_entrypoint()
def merge():
    """Merge existing worker files into main products.jsonl"""
    print("🔄 Merging worker files only...")
    result = merge_worker_files.remote()
    print(f"✅ Merge complete: {result}")

# Usage:
#   modal run modal_build_dataset.py::main              # Run with default 8 workers
#   modal run modal_build_dataset.py::main --num-workers 16  # Run with 16 workers
#   modal run modal_build_dataset.py::merge             # Just merge existing worker files
#
# Download results:
#   modal volume get off-dataset-vol products.jsonl ./products.jsonl
#   modal volume get off-dataset-vol images ./images --recursive
#   modal volume get off-dataset-vol products_worker_*.jsonl ./worker_files/ --recursive

#   modal volume get off-dataset-vol products.jsonl ./products.jsonl