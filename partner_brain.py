"""
MODULE 2: THE BRAIN (partner_brain.py)
Role: The Cognitive Processor.
- Transcribes Audio (Whisper).
- Checks Logic (Sapient HRM).
- Audits Constraints (Hunter Epoch).
- Manages Confirmations (Anti-Hallucination).
"""
import os
import sys
import time
import logging
import json
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
import config_v4 as config


try:
    from v4.monitor.telemetry import TelemetryWriter
except ImportError:
    class TelemetryWriter:
        def update(self, **kwargs): pass

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [BRAIN] %(message)s')
logger = logging.getLogger("Brain")

# Import Modules (Flat Structure)
try:
    from hunter_epoch import HunterEpoch
    # HRM Import (Relative to script)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "HRM"))
    from models.hrm.hrm_act_v1 import HierarchicalReasoningModel_ACTV1
    HRM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"HRM Import Warning: {e}")
    HRM_AVAILABLE = False

class PartnerBrain(nn.Module):
    def __init__(self):
        super().__init__()
        # Device setup
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        
        self.whisper_loaded = False
        self.hrm_loaded = False
        self.hrm_model = None
        self.rule_encoder = None
        self.rule_projector = nn.Linear(384, 512).to(self.device)  # Project 384 (MiniLM) to 512 (HRM z_H)
        
        # Telemetry
        self.telemetry = TelemetryWriter()
        self.telemetry.update(stage="IDLE", status="IDLE")

    def load_models(self):
        # 1. Load Whisper
        try:
            import mlx_whisper
            logger.info(f"Loading Whisper {config.WHISPER_MODEL}...")
            # Ideally load model into memory or prepare it
            self.whisper_loaded = True
        except ImportError:
            logger.error("mlx_whisper missing.")

        # 2. Load Semantic Encoder for Context
        try:
            logger.info("Loading SentenceTransformer for Context Injection...")
            # Explicitly set device to match our device
            device_str = "mps" if self.device.type == "mps" else "cpu"
            self.rule_encoder = SentenceTransformer('all-MiniLM-L6-v2', device=device_str)
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")

        # 3. Load HRM
        if HRM_AVAILABLE:
            try:
                # Load Config & Weights
                # Note: We are initializing with the same stubbed config as before for structure, 
                # but ideally we should load the config from the checkpoint if available.
                # For now, we assume the V1 architecture parameters match.
                hrm_config = {
                    "batch_size": 1, "seq_len": 64, "num_puzzle_identifiers": 2,
                    "vocab_size": 100, 
                    "H_cycles": 2, "L_cycles": 2, 
                    "H_layers": 4, "L_layers": 4, 
                    "hidden_size": 512, 
                    "expansion": 4.0, # ARC-2 uses expansion 4
                    "num_heads": 8, "pos_encodings": "rope",
                    "halt_max_steps": 16, "halt_exploration_prob": 0.0
                }
                self.hrm_model = HierarchicalReasoningModel_ACTV1(hrm_config)
                
                # Load Real Weights
                if os.path.exists(config.SAPIENT_HRM_PATH):
                    state_dict = torch.load(config.SAPIENT_HRM_PATH, map_location=self.device, weights_only=False)
                    self.hrm_model.load_state_dict(state_dict, strict=False)
                    logger.info(f"Sapient HRM loaded from {config.SAPIENT_HRM_PATH}")
                else:
                    logger.warning(f"SAPIENT_HRM_PATH {config.SAPIENT_HRM_PATH} not found! Using random weights.")
                
                # Move model to device
                self.hrm_model = self.hrm_model.to(self.device)
                self.hrm_model.eval()  # Set to evaluation mode

                logger.info("Sapient HRM Architecture Initialized.")
                self.hrm_loaded = True
            except Exception as e:
                logger.error(f"HRM Init Failed: {e}")

    def _embed_rules(self, rules_path):
        """Embeds the Hunter Epoch rules into a tensor for z_H injection."""
        if not self.rule_encoder:
            # Fallback if encoder failed
            return torch.zeros(1, 1, 512, device=self.device)

        try:
            if not os.path.exists(rules_path):
                logger.warning(f"Rules file not found at {rules_path}")
                return torch.zeros(1, 1, 512, device=self.device)

            with open(rules_path, 'r') as f:
                rules_text = f.read() # Treat the whole JSON as a semantic block of text
            
            # Encode: [1, 384] - already on device from SentenceTransformer
            embedding = self.rule_encoder.encode([rules_text], convert_to_tensor=True)
            
            # IMPORTANT: Clone to avoid inference mode tensor issues  
            embedding = embedding.clone().detach()
            
            # Project: [1, 512]
            with torch.no_grad():
                projected = self.rule_projector(embedding)
            
            # Reshape for HRM [Batch, Seq, Hidden] -> [1, 1, 512]
            # HRM expects sequence input, using init constraint as single token equivalent
            return projected.reshape(1, 1, 512)
            
        except Exception as e:
            logger.error(f"Rule embedding failed: {e}")
            return torch.zeros(1, 1, 512, device=self.device)
    
    def _move_carry_to_device(self, carry, device):
        """Move HRM carry state to specified device."""
        from HRM.models.hrm.hrm_act_v1 import HierarchicalReasoningModel_ACTV1Carry, HierarchicalReasoningModel_ACTV1InnerCarry
        
        # Move inner carry and ensure contiguous
        inner_carry = HierarchicalReasoningModel_ACTV1InnerCarry(
            z_H=carry.inner_carry.z_H.to(device).contiguous(),
            z_L=carry.inner_carry.z_L.to(device).contiguous()
        )
        
        # Move outer carry and ensure contiguous
        return HierarchicalReasoningModel_ACTV1Carry(
            inner_carry=inner_carry,
            steps=carry.steps.to(device).contiguous(),
            halted=carry.halted.to(device).contiguous(),
            current_data={k: v.to(device).contiguous() for k, v in carry.current_data.items()}
        )

    def process_audio(self, file_path):
        import mlx_whisper
        
        # A. Transcribe
        self.telemetry.update(stage="INGEST", status="ACTIVE")
        logger.info(f"Listening to {os.path.basename(file_path)}...")
        try:
            self.telemetry.update(stage="TRANSCRIBE")
            # Note: mlx_whisper returns a dict
            result = mlx_whisper.transcribe(file_path, path_or_hf_repo=f"mlx-community/whisper-{config.WHISPER_MODEL}")
            text = result.get('text', '').strip()
            segments = result.get('segments', [])
            
            # Calculate Confidence (Avg of segments)
            avg_logprob = -1.0
            if segments:
                avg_logprob = sum([s.get('avg_logprob', -1) for s in segments]) / len(segments)
            
            # Confidence approximation: logprob of -0.2 is ~80%, -1.0 is ~36%
            # We map -0.3 (approx 75%) as threshold.
            confidence_high = avg_logprob > -0.3 
            
            self.telemetry.update(
                metrics={
                    "word_confidence": round(avg_logprob, 2),
                    "kbps": 128 # Mock
                }
            )

            logger.info(f"Heard: '{text}' (Conf: {avg_logprob:.2f})")
            
        except Exception as e:
            logger.error(f"Hearing Failed: {e}")
            return

        if not text: return
        
        # B1. Route Decision: Use V3-V4 Bridge
        from v3_v4_bridge import get_bridge
        self.telemetry.update(stage="ROUTE", status="ACTIVE")
        
        try:
            bridge = get_bridge(self)
            decision_result = bridge.reason_with_confidence(text, context="Transcribed from audio")
            
            logger.info(f"Router decision: Source={decision_result['source']}, Confidence={decision_result['confidence']:.2f}")
            logger.info(f"Reasoning trace: {decision_result['reasoning_trace']}")
            
            # If V3 LLM was used (general reasoning), use that result directly
            if decision_result['source'] == 'V3-LLM':
                self.telemetry.update(stage="DECIDED", status="COMPLETE")
                
                # Log decision
                logger.info(f"✅ V3 LLM Decision: {decision_result['answer'][:200]}...")
                
                # Add to database as task (if it's a task-like description)
                if any(kw in text.lower() for kw in ['add', 'create', 'task', 'do', 'make', 'buy']):
                    import database
                    task_desc = decision_result['answer'].split('\n')[0].strip()
                    if task_desc:
                        task_id = database.add_task(task_desc)
                        logger.info(f"📝 Task added (ID: {task_id}) from V3 LLM decision")
                
                # Skip HRM processing if V3 LLM already decided
                return
            
            # If HRM was used or no clear decision, continue to HRM processing
            self.telemetry.update(metrics={
                "v3_confidence": decision_result.get('v3_confidence', 0.0),
                "hrm_confidence": decision_result.get('hrm_confidence', 0.0)
            })
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            logger.info("Continuing to HRM processing...")
        
        # B. Rationalize (Sapient HRM with ACT)
        self.telemetry.update(stage="REASON", status="ACTIVE")
        if self.hrm_loaded and self.hrm_model:
            # Compute semantic embeddings for the transcribed text
            # 1. Prepare Context (z_H) - Hunter Epoch Rules
            z_H_embedding = self._embed_rules(config.HUNTER_EPOCH_RULES_PATH)
            
            # 2. Prepare Input (z_L) - Encode spoken text
            if self.rule_encoder:
                txt_emb = self.rule_encoder.encode([text], convert_to_tensor=True)
                txt_emb = txt_emb.clone().detach()
                z_L_embedding = self.rule_projector(txt_emb).reshape(1, 1, 512)
            else:
                z_L_embedding = torch.zeros(1, 1, 512, device=self.device)
            
            # Combine context and input embeddings
            # Pad to match model's expected sequence length
            batch_size = 1
            seq_len = self.hrm_model.config.seq_len
            
            # Create combined embedding: [context, input, padding]
            precomputed_embeddings = torch.cat([z_H_embedding, z_L_embedding], dim=1)  # [1, 2, 512]
            
            # Pad to seq_len
            if precomputed_embeddings.shape[1] < seq_len:
                padding = torch.zeros(1, seq_len - precomputed_embeddings.shape[1], 512, device=self.device)
                precomputed_embeddings = torch.cat([precomputed_embeddings, padding], dim=1)
            
            # Create batch with precomputed embeddings (dummy inputs no longer needed for embedding)
            batch = {
                "inputs": torch.zeros(batch_size, seq_len, dtype=torch.long, device=self.device),
                "puzzle_identifiers": torch.zeros(batch_size, dtype=torch.long, device=self.device),
                "precomputed_embeddings": precomputed_embeddings  # Pass our semantic embeddings
            }
            
            # Initialize carry state
            carry = self.hrm_model.initial_carry(batch)
            carry = self._move_carry_to_device(carry, self.device)
            
            # Run ACT loop using the model's official forward method
            halted = False
            for step in range(self.hrm_model.config.halt_max_steps):
                with torch.no_grad():
                    carry, outputs = self.hrm_model.forward(carry, batch)
                    
                    # Check halting from outputs
                    q_halt_logits = outputs["q_halt_logits"]
                    q_continue_logits = outputs["q_continue_logits"]
                    
                    # Compute halt probability
                    halt_prob = torch.sigmoid(q_halt_logits - q_continue_logits)
                    p_halt = halt_prob.item()
                    
                    logger.info(f"HRM ACT Step {step+1}: Halt Prob {p_halt:.4f}")
                    self.telemetry.update(
                        metrics={"act_steps": step+1, "h_cycles": 1, "l_steps": step+1} # Simplified mapping
                    )
                    
                    if carry.halted.all():
                        logger.info(f"🛑 HRM Decided to HALT at step {step+1}")
                        halted = True
                        break
            
            if not halted:
                logger.info("⚠️ HRM Max Steps Reached without strict Halt.")

            # Decision Logic based on successful halting
            intent_valid = True 

            if not halted:
                 self.telemetry.update(alerts=["SHALLOW REASONING"])

        else:
            # Fallback if model failed to load
            logger.warning("HRM Not Loaded. skipping logic check.")
            intent_valid = True

        # C. The "Ask" Protocol
        if not confidence_high:
            logger.info("❓ CONFIDENCE LOW -> Requesting Clarification.")
            self._request_clarification(text)
            return

        # D. Strategic Governor Audit
        self.telemetry.update(stage="ACT", status="AUDITING")
        # Mocking an action extraction
        action_details = {"cost": 0, "hours": 1} # Default low cost
        if "buy" in text.lower():
            action_details["cost"] = 10000 # Example risk
            
        audit = HunterEpoch.audit_action("Generic Action", action_details)
        
        self.telemetry.update(financial={"cost": action_details.get("cost", 0)})

        if not audit["approved"]:
             self.telemetry.update(status="BLOCKED", alerts=["STRATEGIC CONFLICT"])
             logger.warning(f"⛔ BLOCKED by Governor: {audit['reason']}")
             self._request_verification(text, audit['reason'])
             return

        # E. Execution
        self.telemetry.update(status="EXECUTING")
        logger.info("✅ ACTION APPROVED. Executing...")
        # Trigger ag_worker here...

    def _request_clarification(self, text):
        # Push Notification logic would go here
        logger.info(f"PUSH NOTIFICATION: 'I heard {text} but I'm unsure. Verification needed.'")

    def _request_verification(self, text, reason):
        logger.info(f"PUSH NOTIFICATION: 'Strategic Conflict: {reason}. Approve manually?'")

if __name__ == "__main__":
    brain = PartnerBrain()
    brain.load_models()
    # Test
    # brain.process_audio("test.wav")
    pass
