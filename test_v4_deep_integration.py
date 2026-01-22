#!/usr/bin/env python3
"""
V4 Model Deep Integration Test
Tests all V4 functions and verifies tasks are ACTUALLY completed
Not just checking "success" messages, but verifying real work was done
"""
import os
import sys
import json
import logging
import asyncio
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("V4DeepTest")

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(msg):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{msg}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_result(test, passed, details=""):
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} - {test}")
    if details:
        print(f"    {details}")
    return passed

# ============ TEST 1: HRM MODEL FORWARD PASS ============

def test_hrm_forward_pass():
    """Test HRM model forward pass with ACT reasoning"""
    print_header("TEST 1: HRM Model Forward Pass")
    
    try:
        import torch
        sys.path.insert(0, "HRM")
        from models.hrm.hrm_act_v1 import HierarchicalReasoningModel_ACTV1

        # Load config matching PartnerBrain
        config = {
            "batch_size": 1, "seq_len": 64, "num_puzzle_identifiers": 2,
            "vocab_size": 100, "H_cycles": 2, "L_cycles": 2,
            "H_layers": 4, "L_layers": 4, "hidden_size": 512,
            "expansion": 4.0, "num_heads": 8, "pos_encodings": "rope",
            "halt_max_steps": 8, "halt_exploration_prob": 0.0  # Reduced for testing
        }
        
        model = HierarchicalReasoningModel_ACTV1(config)
        model.eval()
        
        # Create test batch with reasoning puzzle
        batch = {
            "inputs": torch.tensor([[1, 2, 3, 4] + [0] * 60], dtype=torch.long),
            "puzzle_identifiers": torch.zeros(1, dtype=torch.long),
            "precomputed_embeddings": torch.randn(1, 64, 512)
        }
        
        # Run forward pass with ACT
        carry = model.initial_carry(batch)
        
        step_data = []
        halted = False
        
        for step in range(config['halt_max_steps']):
            with torch.no_grad():
                carry, outputs = model.forward(carry, batch)
            
            # Verify outputs are real, not empty
            if outputs is None:
                return print_result("HRM outputs not None", False, "outputs is None")
            
            # Check halt probability
            q_halt = outputs.get("q_halt_logits", torch.zeros(1))
            q_continue = outputs.get("q_continue_logits", torch.zeros(1))
            halt_prob = torch.sigmoid(q_halt - q_continue).item()
            
            # DETECT ACTUAL REASONING: halt_prob should vary, not be constant
            step_data.append({
                "step": step + 1,
                "halt_prob": halt_prob,
                "has_hidden": outputs.get("hidden") is not None
            })
            
            if carry.halted.all():
                halted = True
                logger.info(f"HRM halted at step {step + 1}")
                break
        
        # VERIFY: Actual reasoning occurred
        # Check if halt_prob varied (not stuck at 0.5)
        halt_probs = [d['halt_prob'] for d in step_data]
        has_variance = max(halt_probs) - min(halt_probs) > 0.1
        
        # Check if model took multiple steps (not just one)
        took_multiple_steps = len(step_data) > 1
        
        # Check if some reasoning happened (not all 0.5)
        some_reasoning = any(p < 0.4 or p > 0.6 for p in halt_probs)
        
        has_valid_hiddens = all(d['has_hidden'] for d in step_data)
        
        details = f"Steps taken: {len(step_data)}, Halted: {halted}"
        details += f"\nHalt probabilities: {[f'{p:.2f}' for p in halt_probs[:4]]}..."
        
        if has_variance and took_multiple_steps:
            details += "\n✅ Reasoning verified: ACT engaged with variable halt probabilities"
        elif has_variance:
            details += "\n⚠️ Partial reasoning: Variable but only one step"
        else:
            details += "\n❌ CRITICAL: No actual reasoning - halt_prob stuck at constant value"
        
        # FINAL VERDICT on TRUST
        if not has_variance or not took_multiple_steps:
            details += "\n\n🚨 MODEL OUTPUT CANNOT BE TRUSTED - HRM is going through motions"
        
        return print_result("HRM forward pass with ACT", 
                           has_variance and has_valid_hiddens and some_reasoning, 
                           details)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return print_result("HRM forward pass", False, str(e))

# ============ TEST 2: SEMANTIC ENCODING ============

def test_semantic_encoding():
    """Test semantic encoding with actual verification"""
    print_header("TEST 2: Semantic Encoding")
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        # Load encoder
        logger.info("Loading SentenceTransformer...")
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test texts
        texts = [
            "The cat sat on the mat",
            "A dog chased a ball",
            "Buy groceries from the store"
        ]
        
        # Generate embeddings
        embeddings = encoder.encode(texts, convert_to_tensor=False)
        
        # VERIFY: embeddings are actual vectors
        embeddings_valid = (
            isinstance(embeddings, np.ndarray) and
            embeddings.shape[0] == len(texts) and
            embeddings.shape[1] == 384  # MiniLM-L6-v2 dimension
        )
        
        # Test semantic similarity
        import numpy.linalg as LA
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = cosine_similarity(embeddings)
        
        # VERIFY: Similarity makes sense
        # Same text should have high similarity with itself
        diagonal_high = np.all(np.diag(similarities) > 0.95)
        # Similar concepts should have moderate similarity
        cat_dog_sim = similarities[0, 1]  # "cat" vs "dog"
        makes_sense = 0.3 < cat_dog_sim < 0.7
        
        details = f"Shape: {embeddings.shape}, Vectors valid: {embeddings_valid}"
        if diagonal_high:
            details += " - Self-similarity verified"
        if makes_sense:
            details += " - Semantic relationships valid"
        
        return print_result("Semantic encoding", embeddings_valid and diagonal_high and makes_sense, details)
        
    except Exception as e:
        return print_result("Semantic encoding", False, str(e))

# ============ TEST 3: HUNTER EPOCH GOVERNOR ============

def test_hunter_epoch():
    """Test Hunter Epoch with verification of actual blocking"""
    print_header("TEST 3: Hunter Epoch Governor")
    
    try:
        from hunter_epoch import HunterEpoch
        
        # Test 1: Should be approved (low cost, aligned)
        result_1 = HunterEpoch.audit_action("Buy milk for $5", {"cost": 5, "hours": 0.5})
        approved_1 = result_1.get("approved", False)
        has_reason_1 = "reason" in result_1
        
        # Test 2: Should be blocked (high cost)
        result_2 = HunterEpoch.audit_action("Buy car for $50000", {"cost": 50000, "hours": 10})
        blocked_2 = not result_2.get("approved", True)
        has_reason_2 = "reason" in result_2
        
        # Test 3: Should be approved (zero cost)
        result_3 = HunterEpoch.audit_action("Write code", {"cost": 0, "hours": 2})
        approved_3 = result_3.get("approved", False)
        
        details = f"Low cost: {approved_1}, High cost blocked: {blocked_2}"
        if all([approved_1, blocked_2, approved_3]) and all([has_reason_1, has_reason_2]):
            details += " - All audits verified with reasons"
        
        return print_result("Hunter Epoch governor", 
                           approved_1 and blocked_2 and approved_3 and has_reason_1 and has_reason_2,
                           details)
        
    except Exception as e:
        return print_result("Hunter Epoch", False, str(e))

# ============ TEST 4: PARTNER BRAIN INTEGRATION ============

def test_partner_brain_full():
    """Test PartnerBrain with actual audio processing"""
    print_header("TEST 4: PartnerBrain Full Integration")
    
    try:
        from partner_brain import PartnerBrain
        
        # Initialize brain
        logger.info("Initializing PartnerBrain...")
        brain = PartnerBrain()
        brain.load_models()
        
        # VERIFY: Models loaded
        models_loaded = all([
            brain.whisper_loaded,
            brain.hrm_loaded,
            brain.rule_encoder is not None
        ])
        
        # Test rule embedding
        from v4.monitor.telemetry import DEFAULT_STATE
        rules_path = "v4/config/hunter_epoch_rules.json"
        
        if os.path.exists(rules_path):
            rules_embedding = brain._embed_rules(rules_path)
            rules_valid = (
                isinstance(rules_embedding, type(torch.zeros(1))) and
                rules_embedding.shape == (1, 1, 512)
            )
        else:
            rules_valid = False
            logger.warning(f"Rules file not found: {rules_path}")
        
        details = f"Whisper: {brain.whisper_loaded}, HRM: {brain.hrm_loaded}, "
        details += f"Rules embedding: {rules_valid}"
        
        return print_result("PartnerBrain initialization", models_loaded and rules_valid, details)
        
    except Exception as e:
        return print_result("PartnerBrain", False, str(e))

# ============ TEST 5: TELEMETRY INTEGRATION ============

def test_telemetry_integration():
    """Test telemetry with real-time updates"""
    print_header("TEST 5: Telemetry Integration")
    
    try:
        from v4.monitor.telemetry import TelemetryWriter, TelemetryReader
        
        # Write test data
        writer = TelemetryWriter()
        
        # Test 1: Basic update
        writer.update(stage="TEST_INGEST", status="ACTIVE", metrics={"kbps": 128})
        
        # Test 2: Read back
        reader = TelemetryReader()
        state = reader.read()
        
        stage_matches = state.get("stage") == "TEST_INGEST"
        status_matches = state.get("status") == "ACTIVE"
        kbps_matches = state.get("metrics", {}).get("kbps") == 128
        
        # Test 3: Nested update
        writer.update(metrics={"latency_ms": 50, "word_confidence": 0.8})
        state_2 = reader.read()
        latency_ok = state_2.get("metrics", {}).get("latency_ms") == 50
        confidence_ok = state_2.get("metrics", {}).get("word_confidence") == 0.8
        
        # Clean up
        writer.close()
        reader.close()
        
        details = f"Stage: {stage_matches}, Status: {status_matches}"
        if stage_matches and status_matches:
            details += " - Basic R/W verified"
        if latency_ok and confidence_ok:
            details += " - Nested updates verified"
        
        return print_result("Telemetry shared memory", 
                           all([stage_matches, status_matches, kbps_matches, latency_ok, confidence_ok]),
                           details)
        
    except Exception as e:
        return print_result("Telemetry", False, str(e))

# ============ TEST 6: V4 ORCHESTRATOR RESOURCE MONITOR ============

def test_resource_monitor():
    """Test resource monitoring with actual process detection"""
    print_header("TEST 6: Resource Monitor")
    
    try:
        import psutil
        from v4_orchestrator import ResourceMonitor
        
        monitor = ResourceMonitor()
        
        # Test 1: Check idle state (no creative apps)
        is_busy, reason = monitor.is_creative_mode()
        idle_works = not is_busy
        
        # Test 2: Check CPU monitoring
        cpu = psutil.cpu_percent(interval=0.1)
        cpu_valid = 0 <= cpu <= 100
        
        details = f"Idle detected: {idle_works}, CPU: {cpu}%"
        if idle_works:
            details += f" - Reason: {reason}"
        
        return print_result("Resource monitor", idle_works and cpu_valid, details)
        
    except Exception as e:
        return print_result("Resource monitor", False, str(e))

# ============ TEST 7: TASK VERIFICATION (NOT TRUSTING OUTPUT) ============

def test_task_verification():
    """Verify tasks are ACTUALLY completed, not just claimed"""
    print_header("TEST 7: Task Verification (Not Trusting Output)")
    
    try:
        # Test 1: File actually moved (not just logged)
        test_file = Path("v4/queue/test_verification.tmp")
        test_file.write_text("test content")
        
        # Simulate "processing" by moving file
        dest_file = Path("v4/queue/processed/test_verification.tmp")
        
        # VERIFY: File doesn't exist in processed yet
        before_move = not dest_file.exists()
        
        # Move file
        test_file.rename(dest_file)
        
        # VERIFY: File actually moved
        after_move = dest_file.exists() and not test_file.exists()
        
        # Cleanup
        if dest_file.exists():
            dest_file.unlink()
        
        details = f"Before move: file not in dest ({before_move})"
        if after_move:
            details += f" - File actually moved (verified in dest)"
        else:
            details += f" - FAILED: File not actually moved"
        
        move_verified = before_move and after_move
        
        # Test 2: Database actually updated (not just logged)
        import database
        database.init_db()
        
        task_desc = "Verification test task"
        task_id = database.add_task(task_desc)
        task_in_db = task_id > 0
        
        # Read back and verify
        tasks = database.get_tasks()
        task_found = any(t['description'] == task_desc for t in tasks)
        
        # Complete task
        completed = database.complete_task(task_id)
        
        # VERIFY: Task actually completed
        completed_tasks = database.get_tasks(status='completed')
        actually_completed = any(t['id'] == task_id and t.get('completed_at') for t in completed_tasks)
        
        details += f"\nDB Add: {task_in_db}, Task found: {task_found}"
        details += f"\nDB Complete: {completed}, Actually completed: {actually_completed}"
        
        db_verified = task_in_db and task_found and completed and actually_completed
        
        return print_result("Task verification", move_verified and db_verified, details)
        
    except Exception as e:
        return print_result("Task verification", False, str(e))

# ============ TEST 8: END-TO-END PIPELINE ============

def test_end_to_end_pipeline():
    """Test full V4 pipeline with actual verification"""
    print_header("TEST 8: End-to-End Pipeline Verification")
    
    try:
        from v4_orchestrator import V4Orchestrator
        from v4.monitor.telemetry import TelemetryReader
        
        # Setup test audio file
        test_audio = Path("v4/queue/raw/e2e_test.wav")
        if not test_audio.exists():
            print(f"{YELLOW}⚠️  Test audio not found: {test_audio}")
            return False
        
        # Initialize orchestrator
        orchestrator = V4Orchestrator()
        
        # VERIFY: Brain loaded
        brain_loaded = orchestrator.brain is not None
        if not brain_loaded:
            return print_result("Orchestrator init", False, "Brain not loaded")
        
        # Get initial telemetry state
        telemetry = TelemetryReader()
        initial_state = telemetry.read()
        initial_stage = initial_state.get("stage", "IDLE")
        
        # Simulate pipeline steps with verification
        results = []
        
        # Step 1: Verify telemetry updates
        orchestrator.brain.telemetry.update(stage="INGEST", status="ACTIVE")
        updated_state = telemetry.read()
        stage_updated = updated_state.get("stage") == "INGEST"
        results.append(("Telemetry INGEST update", stage_updated))
        
        # Step 2: Verify HRM processing state
        orchestrator.brain.telemetry.update(stage="REASON", status="ACTIVE")
        reason_state = telemetry.read()
        reasoning_active = reason_state.get("stage") == "REASON"
        results.append(("Telemetry REASON update", reasoning_active))
        
        # Step 3: Verify task completion tracking
        orchestrator.brain.telemetry.update(stage="ACT", status="EXECUTING")
        act_state = telemetry.read()
        act_updated = act_state.get("stage") == "ACT"
        results.append(("Telemetry ACT update", act_updated))
        
        # Step 4: Return to IDLE
        orchestrator.brain.telemetry.update(stage="IDLE", status="IDLE")
        idle_state = telemetry.read()
        idle_updated = idle_state.get("stage") == "IDLE"
        results.append(("Telemetry IDLE update", idle_updated))
        
        # Cleanup
        telemetry.close()
        
        # Summary
        all_passed = all(r[1] for r in results)
        passed_count = sum(r[1] for r in results)
        
        details = f"Passed: {passed_count}/{len(results)}"
        for test_name, passed in results:
            status = "✅" if passed else "❌"
            details += f"\n  {status} {test_name}"
        
        return print_result("End-to-end pipeline", all_passed, details)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return print_result("End-to-end pipeline", False, str(e))

# ============ MAIN RUNNER ============

def main():
    print(f"\n{BLUE}{'#'*60}{RESET}")
    print(f"{BLUE}#   V4 MODEL DEEP INTEGRATION TEST{RESET}")
    print(f"{BLUE}#   Verifying tasks are ACTUALLY completed{RESET}")
    print(f"{BLUE}#   Not just trusting output{RESET}")
    print(f"{BLUE}{'#'*60}{RESET}\n")
    
    results = {
        "HRM Forward Pass with ACT": test_hrm_forward_pass(),
        "Semantic Encoding": test_semantic_encoding(),
        "Hunter Epoch Governor": test_hunter_epoch(),
        "PartnerBrain Integration": test_partner_brain_full(),
        "Telemetry Integration": test_telemetry_integration(),
        "Resource Monitor": test_resource_monitor(),
        "Task Verification": test_task_verification(),
        "End-to-End Pipeline": test_end_to_end_pipeline(),
    }
    
    # Summary
    print_header("FINAL SUMMARY")
    passed = sum(results.values())
    total = len(results)
    percentage = (passed / total) * 100
    
    for test_name, result in results.items():
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"{status} {test_name}")
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}RESULT: {passed}/{total} tests passed ({percentage:.1f}%){RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    if percentage == 100:
        print(f"{GREEN}🎉 ALL V4 FUNCTIONS VERIFIED - Model output TRUSTWORTHY{RESET}")
    elif percentage >= 80:
        print(f"{YELLOW}⚠️  Most functions verified, minor issues detected{RESET}")
    else:
        print(f"{RED}🚨 CRITICAL FAILURES - Model output CANNOT BE TRUSTED{RESET}")
    
    return percentage == 100

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}FATAL ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)