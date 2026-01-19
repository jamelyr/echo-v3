"""
Echo V3 - MLX Intelligence Server
Supports swapping Chat Models AND Embedding Models.
"""

import os
import gc
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

# Paths
# Determines project root assuming this file is in project_root/
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Paths
CHAT_DIRS = [os.path.join(PROJECT_ROOT, "models", "chat")]
EMBED_DIRS = [os.path.join(PROJECT_ROOT, "models", "embeddings")]

# Defaults (Will pick first available if these don't exist)
DEFAULT_CHAT = os.path.join(PROJECT_ROOT, "models", "chat", "Llama-3.2-3B-Instruct-4bit")
DEFAULT_EMBED = os.path.join(PROJECT_ROOT, "models", "embeddings", "all-MiniLM-L6-v2-bf16")

# State
chat_model = None
chat_tokenizer = None
current_chat = DEFAULT_CHAT
current_embed = DEFAULT_EMBED

def list_models_in_dirs(dirs):
    models = []
    for d in dirs:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            if "config.json" in files:
                name = os.path.basename(root)
                # Simple heuristic to categorize if not explicit
                models.append({"id": root, "name": name})
    return models

def save_model_config():
    """Save current model selection to user_config.json"""
    import json
    config_path = os.path.join(PROJECT_ROOT, "user_config.json")
    try:
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
        cfg["chat_model"] = current_chat
        cfg["embed_model"] = current_embed
        with open(config_path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"💾 Saved model config")
    except Exception as e:
        print(f"⚠️ Could not save config: {e}")


def load_chat(path):
    global chat_model, chat_tokenizer, current_chat
    from mlx_lm import load
    import time
    import json
    
    if chat_model:
        print(f"🗑️ Unloading previous model...")
        del chat_model
        del chat_tokenizer
        chat_model = None
        chat_tokenizer = None
        gc.collect()
        # Wait for memory to be freed
        time.sleep(2)
        gc.collect()
        print(f"✅ Memory freed, loading new model...")
    
    try:
        # Pre-check tokenizer_config for known incompatibilities
        tokenizer_config_path = os.path.join(path, "tokenizer_config.json")
        if os.path.exists(tokenizer_config_path):
            with open(tokenizer_config_path) as f:
                tokenizer_config = json.load(f)
            
            # Log tokenizer class for debugging
            tokenizer_class = tokenizer_config.get("tokenizer_class", "Unknown")
            print(f"🔍 Tokenizer class: {tokenizer_class}")
            
            # Known problematic classes that should be skipped
            if tokenizer_class in ["TokenizersBackend", "CustomTokenizer"]:
                print(f"⚠️ Detected potentially incompatible tokenizer class: {tokenizer_class}")
                # Try loading with trust_remote_code to allow custom tokenizers
        
        # Load with max 64k context length
        chat_model, chat_tokenizer = load(
            path,
            tokenizer_config={"model_max_length": 65536}  # 64k context
        )
        current_chat = path
        save_model_config()  # Persist selection
        print(f"✅ Loaded model with 64k context: {os.path.basename(path)}")
        return True, "Loaded with 64k context"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to load model {path}: {error_msg}")
        
        # Provide specific guidance for common errors
        if "TokenizersBackend" in error_msg:
            print(f"💡 Hint: Model has incompatible tokenizer. Check tokenizer_config.json")
        elif "cannot import" in error_msg:
            print(f"💡 Hint: Python version incompatibility. Check dependencies.")
        
        return False, error_msg

def startup():
    # Load from config if available
    path_to_load = DEFAULT_CHAT
    try:
        import json
        config_path = os.path.join(PROJECT_ROOT, "user_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
                if "chat_model" in cfg and os.path.exists(cfg["chat_model"]):
                    path_to_load = cfg["chat_model"]
                    print(f"⚙️ Restoring chat model: {path_to_load}")
    except: pass
    
    ok, msg = load_chat(path_to_load)
    if not ok and path_to_load != DEFAULT_CHAT:
        print(f"⚠️ Falling back to default model: {DEFAULT_CHAT} ({msg})")
        load_chat(DEFAULT_CHAT)

async def chat_completions(request):
    global chat_model, chat_tokenizer
    from mlx_lm import generate
    if not chat_model: return JSONResponse({"error": "No model"}, status_code=500)
    
    body = await request.json()
    messages = body.get("messages", [])
    
    # Use Tokenizer's Chat Template (Critical for correct Llama 3 formatting)
    if hasattr(chat_tokenizer, "apply_chat_template") and chat_tokenizer.chat_template:
        prompt = chat_tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
    else:
        # Fallback (Manual)
        prompt = "\n".join([f"<|{m['role']}|>\n{m['content']}" for m in messages]) + "\n<|assistant|>\n"
    
    stop_tokens = body.get("stop", [])
    
    response = generate(chat_model, chat_tokenizer, prompt=prompt, max_tokens=body.get("max_tokens", 512), verbose=False)
    
    # Handle stop tokens manually since mlx_lm.generate simple API might not
    for stop in stop_tokens:
        if stop in response:
            response = response.split(stop)[0]
    
    return JSONResponse({
        "choices": [{"message": {"role": "assistant", "content": response.strip()}}],
        "model": current_chat
    })

async def list_models(request):
    """Return all AVAILABLE models, marking which ONE is currently loaded"""
    c_models = list_models_in_dirs(CHAT_DIRS)
    e_models = list_models_in_dirs(EMBED_DIRS)
    
    # Filter: Chat shouldn't have 'bert' or 'embed', Embed SHOULD
    chat_filtered = [m for m in c_models if "embed" not in m["name"].lower() and "bert" not in m["name"].lower()]
    embed_filtered = [m for m in e_models if "embed" in m["name"].lower() or "bert" in m["name"].lower() or "minilm" in m["name"].lower()]
    
    return JSONResponse({
        "data": {
            "chat": [{"id": m["id"], "name": m["name"], "selected": m["id"] == current_chat} for m in chat_filtered],
            "embed": [{"id": m["id"], "name": m["name"], "selected": m["id"] == current_embed} for m in embed_filtered]
        }
    })

async def swap_model(request):
    global chat_model, current_chat
    body = await request.json()
    path = body.get("model_path")
    type_ = body.get("type", "chat")
    
    if not path or not os.path.exists(path):
        return JSONResponse({"status": "error", "message": "Invalid model path"}, status_code=500)

    if type_ == "chat":
        # Save old model path in case we need to fallback
        old_chat = current_chat
        ok, msg = load_chat(path)
        if not ok:
            print(f"⚠️ Swap to {path} failed. Attempting to restore {old_chat}...")
            # Try to restore previous model
            ok_restore, msg_restore = load_chat(old_chat)
            if not ok_restore:
                # Last resort: load default
                print(f"⚠️ Restore failed. Loading default model: {DEFAULT_CHAT}...")
                ok_default, msg_default = load_chat(DEFAULT_CHAT)
                if ok_default:
                    return JSONResponse({"status": "error", "message": f"Swap failed ({msg}). Reverted to default model."}, status_code=500)
            return JSONResponse({"status": "error", "message": f"Swap failed ({msg}). Restored previous model."}, status_code=500)
        return JSONResponse({"status": "ok", "message": msg})
    else:
        global current_embed
        current_embed = path
        save_model_config()
        return JSONResponse({"status": "ok", "message": "Embed path updated"})

async def health(request):
    import psutil
    
    # Get memory usage
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_mb = mem_info.rss / (1024 * 1024)  # Convert bytes to MB
    
    return JSONResponse({
        "status": "ok",
        "chat_model": current_chat,
        "embed_model": current_embed,
        "memory_mb": round(mem_mb, 1),
        "memory_gb": round(mem_mb / 1024, 2)
    })

routes = [
    Route("/v1/chat/completions", chat_completions, methods=["POST"]),
    Route("/v1/models", list_models, methods=["GET"]),
    Route("/v1/models/swap", swap_model, methods=["POST"]),
    Route("/health", health, methods=["GET"]),
]

app = Starlette(routes=routes, on_startup=[startup])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=1234)
