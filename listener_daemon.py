"""
MODULE 1: THE SENSORY STREAM (listener_daemon.py)
Role: The Mobile Ear.
- Runs a Socket Server on 0.0.0.0 (Tailscale IP).
- Receives 16kHz PCM chunks.
- Uses Silero VAD to filter silence.
- Upscales to 48kHz (NovaSR).
- Buffers valid speech for specific analysis.
"""
import socket
import threading
import queue
import time
import os
import torch
import numpy as np
import logging
import subprocess

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [EAR] %(message)s')
logger = logging.getLogger("Listener")

# Configuration
HOST = '0.0.0.0'
PORT = 9000  # Tailscale Port
SAMPLE_RATE_IN = 16000
SAMPLE_RATE_OUT = 48000
CHUNK_SIZE = 512  # Audio Chunk Size

# Queues
# Global queue that other modules (like partner_brain) can import or poll from
# In a multi-process setup, we'd use multiprocessing.Queue or a file buffer.
# For this V4 monolithic daemon, a threaded queue works if ran in same process, 
# but listener_daemon is likely its own process.
# We will save chunks to disk for V1 robustness (File-Based Pipeline).
RAW_AUDIO_DIR = os.path.expanduser("~/echo/raw")
os.makedirs(RAW_AUDIO_DIR, exist_ok=True)

class NovaSR:
    """The 52KB Upscaler (Stub/FFmpeg Fallback for V1)"""
    @staticmethod
    def upscale_chunk(audio_data: bytes) -> bytes:
        # In a real implementation: Run inference on the float32 array
        # For V1 speed: We just assume the stream is acceptable or use simple resampling if needed later.
        # Adding a placeholder for the 16k -> 48k logic.
        return audio_data # Pass-through for now to avoid latency delays in python loop

class SileroVAD:
    def __init__(self):
        logger.info("Loading Silero VAD...")
        try:
            # Load from Torch Hub (Cached)
            self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                              model='silero_vad',
                                              force_reload=False,
                                              trust_repo=True)
            (self.get_speech_timestamps, self.save_audio, self.read_audio, self.VADIterator, self.collect_chunks) = utils
            self.model.eval()
            logger.info("Silero VAD Loaded.")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            self.model = None

    def is_speech(self, audio_chunk_float32):
        if self.model is None: return True # Fail open
        # VAD requires tensor input - typical model expects [batch, steps]
        # Silero VAD is finicky with chunk sizes, usually 512 samples at 16k is ok.
        with torch.no_grad():
            speech_prob = self.model(torch.from_numpy(audio_chunk_float32), SAMPLE_RATE_IN).item()
        return speech_prob > 0.5

def handle_client(conn, addr):
    logger.info(f"Connected to {addr}")
    vad = SileroVAD()
    
    # We need a file to write to when speech is detected
    current_file = None
    file_counter = 0
    silence_frames = 0
    
    try:
        while True:
            data = conn.recv(1024) # 1024 bytes = 512 samples (int16)
            if not data: break
            
            # 1. Process VAD
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            if len(audio_int16) < 256: continue 
            
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Silero expects strictly timed chunks, handling stream robustly is complex.
            # For V1 "Mobile Ear", we might enable basic energy/VAD.
            is_speech_frame = vad.is_speech(audio_float32)
            
            if is_speech_frame:
                silence_frames = 0
                if current_file is None:
                    # Start new utterance
                    timestamp = int(time.time())
                    filename = os.path.join(RAW_AUDIO_DIR, f"mobile_{timestamp}.pcm")
                    current_file = open(filename, "wb")
                    logger.info("Speech detected. Recording...")
                
                # 2. Upscale (NovaSR Stub)
                # upscaled = NovaSR.upscale_chunk(data)
                current_file.write(data)
                
            else:
                silence_frames += 1
                # If silence > 1.5 seconds (approx 25 frames if typical loop rate), close file
                if silence_frames > 30 and current_file:
                    logger.info("Silence detected. Closing utterance.")
                    current_file.close()
                    current_file = None
                
    except Exception as e:
        logger.error(f"Connection Error: {e}")
    finally:
        if current_file: current_file.close()
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    logger.info(f"Mobile Ear Listening on {HOST}:{PORT}")
    
    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.daemon = True
        client_thread.start()

if __name__ == "__main__":
    start_server()
