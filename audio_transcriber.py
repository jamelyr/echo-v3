"""
Echo V3 - Audio Transcriber
Cold storage pattern: Load model, transcribe, immediately free RAM.

Model: faster-whisper base.en (int8) - ~150MB loaded, 0MB idle
"""

import gc
import os


def transcribe(file_path: str) -> str:
    """
    Transcribe audio file using faster-whisper.
    
    Cold Storage Pattern:
    1. Load model (only when needed)
    2. Transcribe
    3. Delete model + garbage collect
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return ""
    
    model = None
    try:
        print("🎧 Loading Whisper (base.en, int8)...")
        from faster_whisper import WhisperModel
        
        # CPU + int8 for efficiency on Mac
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        
        print(f"🎧 Transcribing: {os.path.basename(file_path)}")
        segments, info = model.transcribe(file_path, beam_size=5)
        
        # Collect all text
        text = " ".join([segment.text for segment in segments]).strip()
        print(f"✅ Done: {text[:50]}..." if len(text) > 50 else f"✅ Done: {text}")
        
        return text
        
    except ImportError:
        print("❌ faster-whisper not installed. Run: pip install faster-whisper")
        return ""
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""
    finally:
        # CRITICAL: Free RAM immediately
        if model is not None:
            del model
        gc.collect()
        print("🧹 Model unloaded, RAM freed")
