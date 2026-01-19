from huggingface_hub import snapshot_download
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(PROJECT_ROOT, "models", "embeddings", "all-MiniLM-L6-v2-bf16")
REPO = "mlx-community/all-MiniLM-L6-v2-bf16"

os.makedirs(os.path.dirname(DEST), exist_ok=True)
print(f"Downloading {REPO} to {DEST}...")
snapshot_download(repo_id=REPO, local_dir=DEST)
print("✅ Done!")
