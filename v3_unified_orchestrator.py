#!/usr/bin/env python3
"""
V3 Unified Orchestrator (Simplified)
Single entry point for V3-only AI system
No HRM, no complex routing - just V3 LLM
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
import psutil

# V3 Components
from v4_orchestrator import V4Orchestrator, ResourceMonitor
from v4.monitor.telemetry import TelemetryReader, TelemetryWriter, DEFAULT_STATE
from v3_llm_wrapper import get_wrapper

# Config
MONITOR_CONFIG = {
    "refresh_rate": 2,  # 2Hz
    "check_interval": 5,  # Seconds for resource checks
    "mixing_apps": ["Serato DJ Pro", "Resolume Arena 7", "Final Cut Pro", "Logic Pro"],
    "cpu_threshold": 40.0  # Pause if CPU > 40%
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(".run_all_logs/v3_unified.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("V3Unified")


class V3UnifiedOrchestrator:
    """
    Simplified V3-only orchestrator
    V4 Orchestrator for batch processing
    V3 LLM for all reasoning
    V4 Monitor for telemetry
    """
    
    def __init__(self, enable_monitor=True, auto_start=True):
        """
        Initialize simplified V3 orchestrator
        
        Args:
            enable_monitor: If True, start V4 Monitor
            auto_start: If True, start all services automatically
        """
        self.enable_monitor = enable_monitor
        self.running = False
        self.monitor_process = None
        
        # Initialize components
        logger.info("Initializing V3 Unified Orchestrator...")
        
        # V4 Orchestrator (batch processing loop, simplified)
        self.v4_orchestrator = V4Orchestrator()
        
        # V3 LLM Wrapper (all reasoning)
        self.v3_llm = get_wrapper()
        
        # Telemetry Writer
        self.telemetry = TelemetryWriter()
        
        logger.info("✅ V3 Unified Orchestrator initialized (V3-only)")
        
        if auto_start:
            asyncio.create_task(self.start())
    
    async def start(self):
        """Start all V3 services"""
        logger.info("Starting V3 Unified System...")
        self.running = True
        
        # 1. Start V4 Orchestrator (batch processing)
        logger.info("Starting V4 Orchestrator (batch loop)...")
        orchestrator_task = asyncio.create_task(self.v4_orchestrator.run())
        
        # 2. Start V4 Monitor (if enabled)
        if self.enable_monitor:
            logger.info("Starting V4 Monitor...")
            self.monitor_process = await asyncio.create_subprocess_exec(
                [sys.executable, "v4_monitor.py"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info(f"V4 Monitor started (PID: {self.monitor_process.pid})")
        
        # 3. Wait for all services
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            logger.info("V4 Orchestrator cancelled")
        
        # 4. Cleanup
        if self.monitor_process and self.monitor_process.returncode is None:
            logger.info("Stopping V4 Monitor...")
            self.monitor_process.terminate()
            try:
                await asyncio.wait_for(self.monitor_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.monitor_process.kill()
        
        self.running = False
        logger.info("V3 Unified System stopped")
    
    def stop(self):
        """Stop all V3 services"""
        logger.info("Stopping V3 Unified System...")
        self.running = False
        
        self.v4_orchestrator.stop_receiver()
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        telemetry = TelemetryReader()
        state = telemetry.read()
        
        return {
            "v4_orchestrator": {
                "running": self.v4_orchestrator.receiver_process is not None,
                "batch_paused": self.v4_orchestrator.batch_paused
            },
            "v3_llm": {
                "active": state.get("stage") in ["TRANSCRIBE", "V3-LLM", "ACT"],
                "confidence": 0.8  # V3 is consistently good
            },
            "v4_monitor": {
                "enabled": self.enable_monitor,
                "running": self.monitor_process is not None and self.monitor_process.returncode is None
            },
            "telemetry": state,
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "mixing_apps": [
                    proc.info['name'] for proc in psutil.process_iter(['name'])
                    if proc.info['name'] in MONITOR_CONFIG["mixing_apps"]
                ]
            }
        }
    
    async def process_audio_file(self, audio_path: str) -> dict:
        """
        Process audio file through V3 pipeline
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Processing result
        """
        logger.info(f"Processing audio file: {audio_path}")
        
        # Check if file exists
        path = Path(audio_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {audio_path}"
            }
        
        # Use V3 LLM wrapper
        result = self.v3_llm.reason(f"Transcribe and process: {audio_path}")
        
        return {
            "success": True,
            "answer": result.get("answer"),
            "confidence": result.get("confidence"),
            "source": result.get("source")
        }
    
    def print_status(self):
        """Print current system status"""
        status = self.get_system_status()
        
        print("\n" + "="*60)
        print("V3 UNIFIED SYSTEM STATUS")
        print("="*60 + "\n")
        
        print("V4 Orchestrator:")
        print(f"  Running: {status['v4_orchestrator']['running']}")
        print(f"  Batch Paused: {status['v4_orchestrator']['batch_paused']}")
        
        print("\nV3 LLM:")
        print(f"  Active: {status['v3_llm']['active']}")
        print(f"  Confidence: {status['v3_llm']['confidence']:.2f}")
        
        print("\nV4 Monitor:")
        print(f"  Enabled: {status['v4_monitor']['enabled']}")
        print(f"  Running: {status['v4_monitor']['running']}")
        
        print("\nSystem:")
        print(f"  CPU: {status['system']['cpu_percent']:.1f}%")
        print(f"  Mixing Apps: {len(status['system']['mixing_apps'])}")
        
        print("\n" + "="*60)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="V3 Unified Orchestrator (Simplified, No HRM)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command: START
    start_parser = subparsers.add_parser("start", help="Start unified system")
    start_parser.add_argument("--no-monitor", action="store_true", help="Disable V4 Monitor")
    start_parser.add_argument("--status", action="store_true", help="Show status and exit")
    
    # Command: PROCESS
    process_parser = subparsers.add_parser("process", help="Process audio file")
    process_parser.add_argument("audio_path", help="Path to audio file")
    
    # Command: STATUS
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if args.command == "start":
        if args.status:
            orchestrator = V3UnifiedOrchestrator(enable_monitor=not args.no_monitor, auto_start=False)
            orchestrator.print_status()
        else:
            orchestrator = V3UnifiedOrchestrator(enable_monitor=not args.no_monitor, auto_start=True)
            try:
                await orchestrator.start()
            except KeyboardInterrupt:
                orchestrator.stop()
    
    elif args.command == "process":
        orchestrator = V3UnifiedOrchestrator(enable_monitor=False, auto_start=False)
        result = await orchestrator.process_audio_file(args.audio_path)
        
        print("\n" + "="*60)
        print("AUDIO PROCESSING RESULT")
        print("="*60)
        print(f"Success: {result.get('success')}")
        print(f"Source: {result.get('source')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Answer: {result.get('answer', 'N/A')[:200]}...")
        print("="*60 + "\n")
    
    elif args.command == "status":
        orchestrator = V3UnifiedOrchestrator(enable_monitor=False, auto_start=False)
        orchestrator.print_status()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
