"""
Echo V3 - MLX Embeddings
Uses local all-MiniLM-L6-v2-bf16 model for semantic search.

Cold storage pattern: Load when needed, unload after.
"""

import os
import gc

# Path to local embedding model
# Defaults to a safe value, but will be updated by set_model_path
# Path to local embedding model
# Defaults to a safe value, but will be updated by set_model_path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_current_model_path = os.path.join(_PROJECT_ROOT, "models", "embeddings", "all-MiniLM-L6-v2-bf16")

# Cache for model (None when unloaded)
_model = None

def set_model_path(path: str):
    """Update the model path and unload current model to force reload."""
    global _current_model_path
    if path and path != _current_model_path:
        print(f"🔤 Embedding path updated: {path}")
        _current_model_path = path
        unload_model()


def get_embedding(text: str) -> list:
    """
    Get embedding vector for text using local MLX model.
    
    Cold storage pattern:
    - Loads model only when needed
    - Returns embedding vector
    - Model stays loaded for batch operations (caller can call unload_model() after)
    """
    global _model
    
    try:
        # Try mlx-embedding-models first (if installed)
        try:
            from mlx_embedding_models.embedding import EmbeddingModel
            
            if _model is None:
                if os.path.exists(_current_model_path):
                    print(f"🔤 Loading local embedding model: {_current_model_path}")
                    _model = EmbeddingModel.from_pretrained(_current_model_path)
                else:
                    print(f"🔤 Loading embedding model from HuggingFace...")
                    _model = EmbeddingModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            
            # Get embedding
            embeddings = _model.encode([text])
            return embeddings[0].tolist()
            
        except ImportError:
            # Fallback: use sentence-transformers (CPU)
            from sentence_transformers import SentenceTransformer
            
            if _model is None:
                print("🔤 Loading sentence-transformers (CPU fallback)...")
                _model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embedding = _model.encode(text)
            return embedding.tolist()
            
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return []


def unload_model():
    """Unload embedding model to free RAM."""
    global _model
    if _model is not None:
        del _model
        _model = None
        gc.collect()
        print("🧹 Embedding model unloaded")


def get_batch_embeddings(texts: list) -> list:
    """Get embeddings for multiple texts efficiently."""
    global _model
    
    try:
        try:
            from mlx_embedding_models.embedding import EmbeddingModel
            
            if _model is None:
                if os.path.exists(_current_model_path):
                    _model = EmbeddingModel.from_pretrained(_current_model_path)
                else:
                    _model = EmbeddingModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            
            embeddings = _model.encode(texts)
            return [e.tolist() for e in embeddings]
            
        except ImportError:
            from sentence_transformers import SentenceTransformer
            
            if _model is None:
                _model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embeddings = _model.encode(texts)
            return [e.tolist() for e in embeddings]
            
    except Exception as e:
        print(f"❌ Batch embedding error: {e}")
        return [[] for _ in texts]
