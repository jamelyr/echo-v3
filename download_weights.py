from huggingface_hub import hf_hub_download
import os
import shutil

repo_id = "sapientinc/HRM-checkpoint-ARC-2"
filename = "checkpoint"
local_dir = os.path.expanduser("~/echo/brain")
target_name = "sapient_hrm_arc2.bin"

print(f"Downloading {filename} from {repo_id}...")
downloaded_path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir)

target_path = os.path.join(local_dir, target_name)
print(f"Renaming {downloaded_path} to {target_path}...")
shutil.move(downloaded_path, target_path)

print("Download complete.")
