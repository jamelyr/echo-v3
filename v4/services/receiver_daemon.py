"""
Echo V4 Receiver Daemon
High-performance audio ingestion service.
Receives OPUS audio chunks, upscales via NovaSR, and queues for processing.
"""

import os
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import aiofiles
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ReceiverDaemon")

# Configuration
PORT = 5555
HOST = "0.0.0.0" # Listen on all interfaces (Tailscale IP)
QUEUE_DIR = Path(os.path.expanduser("~/Documents/ag/v4/queue"))
RAW_DIR = QUEUE_DIR / "raw"
UPSCALED_DIR = QUEUE_DIR / "upscaled"
PROCESSED_DIR = QUEUE_DIR / "processed"

# Ensure directories exist
for d in [RAW_DIR, UPSCALED_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Echo V4 Receiver")

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Receiver Daemon starting on port {PORT}")
    logger.info(f"📂 Queue directory: {QUEUE_DIR}")

@app.post("/ingest")
async def ingest_audio(file: UploadFile = File(...)):
    """
    Receive OPUS audio chunk from phone.
    """
    try:
        start_time = time.time()
        
        # Generate filename
        timestamp = int(start_time * 1000)
        filename = f"{timestamp}_{file.filename}"
        raw_path = RAW_DIR / filename
        
        # Write raw chunk to disk (Real-time capture)
        async with aiofiles.open(raw_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        logger.debug(f"📥 Received {len(content)} bytes -> {raw_path.name} in {(time.time() - start_time)*1000:.2f}ms")
        
        # Trigger async processing (Fire and forget from client perspective)
        # In a real UDP scenario, we wouldn't await. For HTTP, we return quick 200.
        asyncio.create_task(process_chunk(raw_path))
        
        return {"status": "received", "id": filename}
        
    except Exception as e:
        logger.error(f"❌ Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_chunk(raw_path: Path):
    """
    Hybrid Processing Pipeline:
    1. NovaSR Upscale (Real-time)
    2. VAD Check (Real-time)
    3. Queue for Transcription (Batched/Idle)
    """
    try:
        # Placeholder: Copy raw to upscaled for now
        upscaled_path = UPSCALED_DIR / raw_path.name
        
        # Mock NovaSR: just copy/rename
        import shutil
        shutil.copy(raw_path, upscaled_path)
        logger.info(f"✨ Mock Upscale: {raw_path.name} -> {upscaled_path}")
        
        # In real life, VAD check would happen here


    except Exception as e:
        logger.error(f"Processing error for {raw_path}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
