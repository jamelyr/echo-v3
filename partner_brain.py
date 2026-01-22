#!/usr/bin/env python3
"""
PartnerBrain (Simplified - HRM Removed)
Audio transcription and processing using V3 LLM
"""
import os
import sys
import logging
import torch
from pathlib import Path
from typing import Optional, Dict, Any

# Whisper for audio transcription
import mlx_whisper

# V3 components
import llm_client
import database
import config_v4 as config
from v4.monitor.telemetry import TelemetryWriter, DEFAULT_STATE
from hunter_epoch import HunterEpoch

logger = logging.getLogger("PartnerBrain")

class PartnerBrain:
    """
    Simplified PartnerBrain without HRM
    - Whisper transcription
    - V3 LLM reasoning (instead of HRM)
    - Hunter Epoch governor
    - Telemetry updates
    """
    
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        
        # Whisper model
        self.whisper_loaded = False
        self.whisper_model = None
        
        # Semantic encoder (MiniLM for context)
        self.rule_encoder = None
        self.rule_projector = None
        
        # Telemetry writer
        self.telemetry = TelemetryWriter()
        
        logger.info(f"🧠 PartnerBrain initialized (Device: {self.device})")
    
    def load_models(self):
        """Load Whisper and encoder models"""
        logger.info("Loading models...")
        
        # 1. Load Whisper (will load on-demand)
        self.whisper_loaded = True
        logger.info("✅ Whisper ready (will load on-demand)")
        
        # 2. Load SentenceTransformer encoder (for context injection if needed)
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer for Context Injection...")
            self.rule_encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create projector to map 384-dim embeddings to hidden size
            hidden_size = 512
            self.rule_projector = torch.nn.Linear(384, hidden_size).to(self.device)
            
            logger.info("✅ SentenceTransformer loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}")
            self.rule_encoder = None
        
        # Update telemetry
        self.telemetry.update(metrics={"model_loaded": True})
    
    def process_audio(self, file_path):
        """
        Process audio file:
        1. Transcribe with Whisper
        2. Send to V3 LLM for reasoning
        3. Audit with Hunter Epoch
        4. Execute if approved
        """
        import mlx_whisper
        
        # A. Transcribe
        self.telemetry.update(stage="INGEST", status="ACTIVE")
        logger.info(f"Listening to {os.path.basename(file_path)}...")
        
        try:
            self.telemetry.update(stage="TRANSCRIBE")
            result = mlx_whisper.transcribe(file_path, path_or_hf_repo=f"mlx-community/whisper-{config.WHISPER_MODEL}")
            text = result.get('text', '').strip()
            segments = result.get('segments', [])
            
            # Calculate Confidence (Avg of segments)
            avg_logprob = -1.0
            if segments:
                avg_logprob = sum([s.get('avg_logprob', -1) for s in segments]) / len(segments)
            
            # Confidence approximation: logprob of -0.3 is ~80%, -1.0 is ~36%
            # We map -0.3 (approx 75%) as threshold.
            confidence_high = avg_logprob > -0.3 
            
            self.telemetry.update(
                metrics={
                    "word_confidence": round(avg_logprob, 2),
                    "kbps": 128
                }
            )
            
            logger.info(f"Heard: '{text}' (Conf: {avg_logprob:.2f})")
            
        except Exception as e:
            logger.error(f"Hearing Failed: {e}")
            return
        
        if not text: return
        
        # B. V3 LLM Reasoning (Instead of HRM)
        self.telemetry.update(stage="REASON", status="ACTIVE")
        
        try:
            # Build prompt for V3 LLM
            prompt = f"User said (transcribed from audio): {text}\n\nPlease respond helpfully."
            
            # Call V3 LLM (async)
            import asyncio
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                llm_client.process_input(prompt, user_id="audio_input", history=[])
            )
            
            logger.info(f"V3 LLM Response: {response[:200]}...")
            
            # Extract action from response if present
            # Check if response contains task-related content
            if any(kw in text.lower() for kw in ['add task', 'create task', 'task:']):
                # Try to add task to database
                task_desc = response.split('\n')[0].strip()
                if task_desc and task_desc not in ['Task added', 'Ok', 'Done']:
                    task_id = database.add_task(task_desc)
                    logger.info(f"📝 Task added (ID: {task_id})")
                    
                    action_details = {"cost": 0, "hours": 0}
                else:
                    # No task to add
                    action_details = {"cost": 0, "hours": 0}
            else:
                # General conversation
                action_details = {"cost": 0, "hours": 0}
            
            self.telemetry.update(stage="DECIDED", status="COMPLETE")
            
        except Exception as e:
            logger.error(f"V3 LLM reasoning failed: {e}")
            action_details = {"cost": 0, "hours": 0}
        
        # C. The "Ask" Protocol (low confidence)
        if not confidence_high:
            logger.info("❓ CONFIDENCE LOW -> Requesting Clarification.")
            self._request_clarification(text)
            return
        
        # D. Strategic Governor Audit
        self.telemetry.update(stage="ACT", status="AUDITING")
        
        # Extract cost from text (simple detection)
        if "buy" in text.lower() or "purchase" in text.lower():
            # Look for currency/number patterns
            import re
            cost_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:rs|usd|inr|$', text, re.IGNORECASE)
            if cost_match:
                cost = float(cost_match.group(1))
                action_details["cost"] = cost
        elif "hour" in text.lower() or "spend" in text.lower():
            action_details["hours"] = 2
        
        audit = HunterEpoch.audit_action("Audio Action", action_details)
        
        self.telemetry.update(financial={"cost": action_details.get("cost", 0)})
        
        if not audit["approved"]:
            self.telemetry.update(status="BLOCKED", alerts=["STRATEGIC CONFLICT"])
            logger.warning(f"⛔ BLOCKED by Governor: {audit['reason']}")
            self._request_verification(text, audit['reason'])
            return
        
        # E. Execution (log for now, would connect to Ag Worker)
        self.telemetry.update(status="EXECUTING")
        logger.info("✅ ACTION APPROVED. Ready to execute...")
        
        # TODO: Connect to Ag Worker here
        # For now, just log the decision
        logger.info(f"Decision to execute: {text}")
    
    def _request_clarification(self, text):
        """Request clarification from user"""
        logger.info(f"PUSH NOTIFICATION: 'I heard {text} but I'm unsure. Verification needed.'")
    
    def _request_verification(self, text, reason):
        """Request manual verification"""
        logger.info(f"PUSH NOTIFICATION: 'Strategic Conflict: {reason}. Approve manually?'")


if __name__ == "__main__":
    brain = PartnerBrain()
    brain.load_models()
    
    # Test with audio file if exists
    test_audio = "v4/queue/raw/e2e_test.wav"
    if os.path.exists(test_audio):
        brain.process_audio(test_audio)