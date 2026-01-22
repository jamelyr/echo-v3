#!/usr/bin/env python3
"""
V3+V4 Unified Orchestrator
Single entry point for unified AI system
Combines V4 Orchestrator, V3-V4 Bridge, and V4 Monitor
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
import psutil

# V4 Components
from v4_orchestrator import V4Orchestrator, ResourceMonitor
from v4.monitor.telemetry import TelemetryReader, TelemetryWriter, DEFAULT_STATE

# V3-V4 Bridge
try:
    from v3_v4_bridge import get_bridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

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
        logging.FileHandler(".run_all_logs/v3_v4_unified.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("V3V4Unified")


class V3V4UnifiedOrchestrator:
    """
    Unified orchestrator for V3 + V4 system
    Combines V4 batch processing, V3-V4 bridge routing, and V4 monitoring
    """
    
    def __init__(self, enable_monitor=True, auto_start=True):
        """
        Initialize unified orchestrator
        
        Args:
            enable_monitor: If True, start V4 Monitor
            auto_start: If True, start all services automatically
        """
        self.enable_monitor = enable_monitor
        self.running = False
        self.monitor_process = None
        
        # Initialize components
        logger.info("Initializing V3+V4 Unified Orchestrator...")
        
        # V4 Orchestrator (batch processing loop)
        self.v4_orchestrator = V4Orchestrator()
        
        # V3-V4 Bridge (decision routing)
        self.bridge = get_bridge(self.v4_orchestrator.brain) if BRIDGE_AVAILABLE else None
        if self.bridge:
            logger.info("V3-V4 Bridge loaded successfully")
        else:
            logger.warning("V3-V4 Bridge not available")
        
        # Telemetry Writer (for unified system state)
        self.telemetry = TelemetryWriter()
        
        logger.info("✅ V3+V4 Unified Orchestrator initialized")
        
        if auto_start:
            asyncio.create_task(self.start())
    
    async def start(self):
        """
        Start all unified system services
        """
        logger.info("Starting V3+V4 Unified System...")
        self.running = True
        
        # 1. Start V4 Orchestrator (batch processing)
        logger.info("Starting V4 Orchestrator...")
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
        logger.info("V3+V4 Unified System stopped")
    
    def stop(self):
        """
        Stop all unified system services
        """
        logger.info("Stopping V3+V4 Unified System...")
        self.running = False
        
        # Stop V4 Orchestrator
        self.v4_orchestrator.stop_receiver()
        
        # V4 Monitor will be stopped by start() method
    
    def get_system_status(self) -> dict:
        """
        Get current system status
        
        Returns:
            Dict with system status information
        """
        telemetry = TelemetryReader()
        state = telemetry.read()
        
        return {
            "v4_orchestrator": {
                "running": self.v4_orchestrator.receiver_process is not None,
                "brain_loaded": self.v4_orchestrator.brain is not None,
                "batch_paused": self.v4_orchestrator.batch_paused
            },
            "v4_monitor": {
                "enabled": self.enable_monitor,
                "running": self.monitor_process is not None and self.monitor_process.returncode is None
            },
            "bridge": {
                "available": BRIDGE_AVAILABLE,
                "v3_llm_active": state.get("metrics", {}).get("v3_confidence", 0) > 0.5,
                "hrm_active": state.get("stage") in ["REASON", "ENCODE"]
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
    
    async def process_audio_file(self, audio_path: str, require_verification: bool = False) -> dict:
        """
        Process audio file through unified pipeline
        
        Args:
            audio_path: Path to audio file
            require_verification: If True, require manual verification for low confidence
        
        Returns:
            Processing result with decision details
        """
        logger.info(f"Processing audio file: {audio_path}")
        
        # Check if file exists
        path = Path(audio_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {audio_path}"
            }
        
        # 1. Transcribe using PartnerBrain (V4)
        logger.info("Step 1: Transcribing audio...")
        try:
            # Note: PartnerBrain.process_audio() doesn't return text directly
            # It processes through the pipeline and updates telemetry
            # We'll use V3-V4 Bridge for decision making instead
            if self.bridge:
                # Mock transcription for now (would need Whisper)
                transcribed_text = f"Transcribed from {os.path.basename(audio_path)}"
                
                logger.info("Step 2: Routing decision...")
                decision = self.bridge.route_with_verification(
                    transcribed_text,
                    context="Audio input from unified orchestrator",
                    require_verification=require_verification
                )
                
                result = {
                    "success": decision.get("confidence", 0) > 0.5,
                    "transcription": transcribed_text,
                    "decision": decision.get("answer"),
                    "confidence": decision.get("confidence"),
                    "source": decision.get("source"),
                    "requires_verification": decision.get("requires_verification", False),
                    "reasoning_trace": decision.get("reasoning_trace")
                }
                
                logger.info(f"Decision complete: {decision.get('source')} (confidence: {decision.get('confidence'):.2f})")
                
                return result
            else:
                return {
                    "success": False,
                    "error": "V3-V4 Bridge not available"
                }
        
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def print_status(self):
        """
        Print current system status to console
        """
        status = self.get_system_status()
        
        print("\n" + "="*60)
        print("V3+V4 UNIFIED SYSTEM STATUS")
        print("="*60 + "\n")
        
        print("V4 Orchestrator:")
        print(f"  Running: {status['v4_orchestrator']['running']}")
        print(f"  Brain Loaded: {status['v4_orchestrator']['brain_loaded']}")
        print(f"  Batch Paused: {status['v4_orchestrator']['batch_paused']}")
        
        print("\nV4 Monitor:")
        print(f"  Enabled: {status['v4_monitor']['enabled']}")
        print(f"  Running: {status['v4_monitor']['running']}")
        
        print("\nV3-V4 Bridge:")
        print(f"  Available: {status['bridge']['available']}")
        print(f"  V3 LLM Active: {status['bridge']['v3_llm_active']}")
        print(f"  HRM Active: {status['bridge']['hrm_active']}")
        
        print("\nSystem:")
        print(f"  CPU: {status['system']['cpu_percent']:.1f}%")
        print(f"  Mixing Apps: {len(status['system']['mixing_apps'])}")
        
        print("\n" + "="*60)


async def main():
    """
    Main entry point for V3+V4 Unified Orchestrator
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="V3+V4 Unified Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command: START (Start unified system)
    start_parser = subparsers.add_parser("start", help="Start unified system")
    start_parser.add_argument("--no-monitor", action="store_true", help="Disable V4 Monitor")
    start_parser.add_argument("--status", action="store_true", help="Show status and exit")
    
    # Command: PROCESS (Process single audio file)
    process_parser = subparsers.add_parser("process", help="Process audio file")
    process_parser.add_argument("audio_path", help="Path to audio file")
    process_parser.add_argument("--verify", action="store_true", help="Require verification for low confidence")
    
    # Command: STATUS (Show system status)
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if args.command == "start":
        if args.status:
            # Just show status
            orchestrator = V3V4UnifiedOrchestrator(enable_monitor=not args.no_monitor, auto_start=False)
            orchestrator.print_status()
        else:
            # Start system
            orchestrator = V3V4UnifiedOrchestrator(enable_monitor=not args.no_monitor, auto_start=True)
            try:
                await orchestrator.start()
            except KeyboardInterrupt:
                orchestrator.stop()
    
    elif args.command == "process":
        orchestrator = V3V4UnifiedOrchestrator(enable_monitor=False, auto_start=False)
        result = await orchestrator.process_audio_file(args.audio_path, args.verify)
        
        print("\n" + "="*60)
        print("AUDIO PROCESSING RESULT")
        print("="*60)
        print(f"Success: {result.get('success')}")
        print(f"Source: {result.get('source')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Decision: {result.get('decision', 'N/A')[:200]}...")
        print(f"Requires Verification: {result.get('requires_verification', False)}")
        
        if not result.get('success'):
            print(f"Error: {result.get('error')}")
        
        print("="*60 + "\n")
    
    elif args.command == "status":
        orchestrator = V3V4UnifiedOrchestrator(enable_monitor=False, auto_start=False)
        orchestrator.print_status()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())