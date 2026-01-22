"""
Echo V4 Orchestrator (The Conductor)
Manages V4 services and implements the "Golden Ball Guard" resource monitor.
"""

import os
import sys
import time
import subprocess
import logging
import psutil
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Orchestrator] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(".run_all_logs/v4_orchestrator.log")
    ]
)
logger = logging.getLogger("V4Orchestrator")

# Configuration
CREATIVE_APPS = ["Serato DJ Pro", "Resolume Arena", "Final Cut Pro", "Logic Pro"]
CPU_THRESHOLD = 40.0 # Pause if CPU > 40%
CHECK_INTERVAL = 5 # Seconds

RECEIVER_SCRIPT = "v4/services/receiver_daemon.py"
HRM_SCRIPT = "v4/services/hrm_governor.py"

# Import PartnerBrain for actual HRM processing
from partner_brain import PartnerBrain

class ResourceMonitor:
    def is_creative_mode(self):
        """Check if we are in a high-performance creative session"""
        # 1. Check active processes
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in CREATIVE_APPS:
                    return True, f"Creative App Active: {proc.info['name']}"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # 2. Check System Load
        cpu_usage = psutil.cpu_percent(interval=0.1)
        if cpu_usage > CPU_THRESHOLD:
            return True, f"High CPU Load: {cpu_usage}%"
            
        return False, "System Idle"

class V4Orchestrator:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.receiver_process = None
        self.batch_paused = False
        self.brain = None
        self._init_brain()
    
    def _init_brain(self):
        """Initialize PartnerBrain with HRM and Whisper models."""
        try:
            logger.info("🧠 Initializing PartnerBrain...")
            self.brain = PartnerBrain()
            self.brain.load_models()
            logger.info("✅ PartnerBrain loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PartnerBrain: {e}")
            self.brain = None
        
    def start_receiver(self):
        """Start the high-performance audio ingestion daemon"""
        logger.info(f"🚀 Starting Receiver Daemon ({RECEIVER_SCRIPT})...")
        try:
            self.receiver_process = subprocess.Popen(
                [sys.executable, RECEIVER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"✅ Receiver running (PID: {self.receiver_process.pid})")
        except Exception as e:
            logger.error(f"❌ Failed to start receiver: {e}")

    def stop_receiver(self):
        if self.receiver_process:
            logger.info("🛑 Stopping Receiver Daemon...")
            self.receiver_process.terminate()
            self.receiver_process = None

    async def batch_processing_loop(self):
        """
        The 'Thinking' Loop (Whisper + HRM)
        Only runs when system is 'Idle'.
        """
        logger.info("🎻 Batch Processing Loop initialized")
        
        while True:
            is_busy, reason = self.monitor.is_creative_mode()
            
            if is_busy:
                if not self.batch_paused:
                    logger.warning(f"⏸️  PAUSING Batch Processor | Reason: {reason}")
                    self.batch_paused = True
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            if self.batch_paused:
                logger.info("▶️  RESUMING Batch Processor | System Idle")
                self.batch_paused = False
            
            # Real Processing: Check for upscaled files and process with PartnerBrain
            queue_dir = Path(os.path.expanduser("~/Documents/ag/v4/queue/upscaled"))
            processed_dir = Path(os.path.expanduser("~/Documents/ag/v4/queue/processed"))
            
            if queue_dir.exists() and self.brain:
                for f in queue_dir.glob("*.wav"):
                    logger.info(f"🧠 Processing {f.name} with PartnerBrain...")
                    
                    try:
                        # Call PartnerBrain to process audio (Whisper + HRM + Governor)
                        self.brain.process_audio(str(f))
                        
                        # Move to processed after successful processing
                        dest = processed_dir / f.name
                        f.rename(dest)
                        logger.info(f"✅ Completed and moved to: {dest}")
                    except Exception as e:
                        logger.error(f"❌ Failed to process {f.name}: {e}")
                    
                    break # Process one at a time
            
            await asyncio.sleep(1)

    async def run(self):
        self.start_receiver()
        try:
            await self.batch_processing_loop()
        except asyncio.CancelledError:
            logger.info("Orchestrator stopped")
        finally:
            self.stop_receiver()

def main():
    orchestrator = V4Orchestrator()
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
