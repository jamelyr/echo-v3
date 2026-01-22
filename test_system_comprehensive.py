#!/usr/bin/env python3
"""
Comprehensive Echo V3 & V4 System Test
Tests all components and reports status
"""
import os
import sys
import asyncio
import subprocess
import time
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SystemTest")

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(msg):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{msg}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_result(test_name, passed, details=""):
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")

# ============ V3 TESTS ============

def test_v3_database():
    """Test database connectivity and schema"""
    print_header("V3 DATABASE TEST")
    try:
        import database
        database.init_db()

        # Test task operations
        database.add_task("Test task for system validation")
        tasks = database.get_tasks()  # Fixed: was list_tasks

        # Test note operations
        database.add_note("Test note for validation", None)
        notes = database.get_similar_notes("test", 5)

        print_result("Database operations", len(tasks) > 0, f"Found {len(tasks)} pending tasks")
        return True
    except Exception as e:
        print_result("Database operations", False, str(e))
        return False

def test_v3_embeddings():
    """Test MLX embeddings model"""
    print_header("V3 EMBEDDINGS TEST")
    try:
        import mlx_embeddings
        import numpy as np
        embedding = mlx_embeddings.get_embedding("test text")
        valid = embedding is not None and len(embedding) > 0
        # Fixed: check if it's numpy array or list
        shape = embedding.shape if hasattr(embedding, 'shape') else len(embedding) if hasattr(embedding, '__len__') else 'Unknown'
        print_result("MLX Embeddings", valid, f"Shape/Size: {shape}")
        return valid
    except Exception as e:
        print_result("MLX Embeddings", False, str(e))
        return False

def test_v3_llm_client():
    """Test llm_client tool execution"""
    print_header("V3 LLM CLIENT TEST")
    try:
        import llm_client

        # Fixed: Test tool execution instead of list_tasks (doesn't exist)
        result = llm_client.execute_tool("add_task", {"description": "Tool test"})
        tool_works = result is not None

        print_result("LLM Client tool execution", tool_works)
        return tool_works
    except Exception as e:
        print_result("LLM Client", False, str(e))
        return False

def test_v3_config():
    """Test user config loading"""
    print_header("V3 CONFIG TEST")
    try:
        import json
        config_file = "user_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                cfg = json.load(f)
            print_result("User config", True, f"Keys: {list(cfg.keys())}")
            return True
        else:
            print_result("User config", False, "File not found")
            return False
    except Exception as e:
        print_result("User config", False, str(e))
        return False

# ============ V4 TESTS ============

def test_v4_partner_brain():
    """Test PartnerBrain model loading"""
    print_header("V4 PARTNER BRAIN TEST")
    try:
        from partner_brain import PartnerBrain
        import torch

        brain = PartnerBrain()
        brain.load_models()

        results = {
            "Whisper loaded": brain.whisper_loaded,
            "HRM loaded": brain.hrm_loaded,
            "Rule encoder loaded": brain.rule_encoder is not None,
            "Device": str(brain.device)
        }

        print_result("PartnerBrain initialization", all([
            brain.whisper_loaded,
            brain.hrm_loaded,
            brain.rule_encoder is not None
        ]), f"Whisper: {brain.whisper_loaded}, HRM: {brain.hrm_loaded}, Device: {brain.device}")
        return brain.hrm_loaded
    except Exception as e:
        print_result("PartnerBrain", False, str(e))
        return False

def test_v4_telemetry():
    """Test telemetry shared memory"""
    print_header("V4 TELEMETRY TEST")
    try:
        from v4.monitor.telemetry import TelemetryWriter, TelemetryReader, DEFAULT_STATE

        # Write test
        writer = TelemetryWriter()
        writer.update(stage="TEST", status="ACTIVE")

        # Read test
        reader = TelemetryReader()
        state = reader.read()

        valid = state.get('stage') == 'TEST'
        print_result("Telemetry shared memory", valid, f"Stage: {state.get('stage')}")
        writer.close()
        reader.close()
        return valid
    except Exception as e:
        print_result("Telemetry", False, str(e))
        return False

def test_v4_orchestrator():
    """Test V4 Orchestrator initialization"""
    print_header("V4 ORCHESTRATOR TEST")
    try:
        from v4_orchestrator import V4Orchestrator
        from partner_brain import PartnerBrain

        orchestrator = V4Orchestrator()

        results = {
            "Monitor initialized": orchestrator.monitor is not None,
            "PartnerBrain loaded": orchestrator.brain is not None,
            "HRM in brain": orchestrator.brain.hrm_loaded if orchestrator.brain else False
        }

        all_ok = all([
            orchestrator.monitor is not None,
            orchestrator.brain is not None,
            orchestrator.brain.hrm_loaded if orchestrator.brain else False
        ])

        print_result("V4 Orchestrator init", all_ok, f"Brain loaded: {orchestrator.brain is not None}")
        return all_ok
    except Exception as e:
        print_result("V4 Orchestrator", False, str(e))
        return False

def test_v4_hrm_model():
    """Test HRM model forward pass"""
    print_header("V4 HRM MODEL TEST")
    try:
        import torch
        import sys
        sys.path.insert(0, "HRM")
        from models.hrm.hrm_act_v1 import HierarchicalReasoningModel_ACTV1

        # Initialize model
        config = {
            "batch_size": 1, "seq_len": 64, "num_puzzle_identifiers": 2,
            "vocab_size": 100, "H_cycles": 2, "L_cycles": 2,
            "H_layers": 4, "L_layers": 4, "hidden_size": 512,
            "expansion": 4.0, "num_heads": 8, "pos_encodings": "rope",
            "halt_max_steps": 16, "halt_exploration_prob": 0.0
        }
        model = HierarchicalReasoningModel_ACTV1(config)
        model.eval()

        # Test forward pass
        batch = {
            "inputs": torch.randint(0, 100, (1, 64)),
            "puzzle_identifiers": torch.zeros(1, dtype=torch.long),
            "precomputed_embeddings": torch.randn(1, 64, 512)
        }

        carry = model.initial_carry(batch)
        carry, outputs = model.forward(carry, batch)

        has_output = outputs is not None
        has_carry = carry is not None
        print_result("HRM forward pass", has_output and has_carry, f"Carry type: {type(carry).__name__}")
        return has_output and has_carry
    except Exception as e:
        print_result("HRM model", False, str(e))
        return False

def test_v4_hunter_epoch():
    """Test Hunter Epoch governor"""
    print_header("V4 HUNTER EPOCH TEST")
    try:
        from hunter_epoch import HunterEpoch

        # Test audit
        result = HunterEpoch.audit_action("test_action", {"cost": 100, "hours": 1})

        approved = result.get("approved", False)
        has_reason = "reason" in result

        print_result("Hunter Epoch audit", approved and has_reason, f"Reason: {result.get('reason')}")
        return approved and has_reason
    except Exception as e:
        print_result("Hunter Epoch", False, str(e))
        return False

def test_v4_monitor():
    """Test V4 Monitor reader"""
    print_header("V4 MONITOR TEST")
    try:
        from v4.monitor.telemetry import TelemetryReader, DEFAULT_STATE

        reader = TelemetryReader()
        state = reader.read()

        valid = isinstance(state, dict) and "stage" in state
        print_result("V4 Monitor reader", valid, f"Stage: {state.get('stage')}")
        reader.close()
        return valid
    except Exception as e:
        print_result("V4 Monitor", False, str(e))
        return False

# ============ INTEGRATION TESTS ============

def test_file_structure():
    """Test required files and directories exist"""
    print_header("FILE STRUCTURE TEST")
    checks = []

    required_files = [
        ("web_server.py", "V3 Web Server"),
        ("llm_client.py", "V3 LLM Client"),
        ("database.py", "V3 Database"),
        ("partner_brain.py", "V4 Partner Brain"),
        ("v4_orchestrator.py", "V4 Orchestrator"),
        ("hunter_epoch.py", "V4 Hunter Epoch"),
        ("v4_monitor.py", "V4 Monitor"),
        ("run_all.sh", "Launcher Script"),
    ]

    for file, desc in required_files:
        exists = os.path.exists(file)
        checks.append(exists)
        print_result(desc, exists)

    all_exist = all(checks)
    print_result("File structure", all_exist, f"{sum(checks)}/{len(checks)} files present")
    return all_exist

def test_hrm_weights():
    """Test HRM model weights file exists"""
    print_header("HRM MODEL WEIGHTS TEST")
    try:
        import config_v4 as config
        weights_path = config.SAPIENT_HRM_PATH
        exists = os.path.exists(weights_path)
        size_mb = os.path.getsize(weights_path) / (1024*1024) if exists else 0
        print_result("HRM weights file", exists, f"Path: {weights_path}, Size: {size_mb:.1f} MB")
        return exists
    except Exception as e:
        print_result("HRM weights", False, str(e))
        return False

def test_database_integrity():
    """Test database tables and data"""
    print_header("DATABASE INTEGRITY TEST")
    try:
        import database
        # Use the same DB connection that init_db creates
        database.init_db()

        # Check tables using database module's connection
        import sqlite3
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['tasks', 'notes', 'chat_history', 'processed_messages']
        has_all_tables = all(t in tables for t in expected_tables)

        print_result("Database tables", has_all_tables, f"Tables: {tables}")

        # Check counts (if tasks table exists)
        if 'tasks' in tables:
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            print_result("Task count", task_count >= 0, f"{task_count} tasks")

        conn.close()
        return has_all_tables
    except Exception as e:
        print_result("Database integrity", False, str(e))
        return False

# ============ MAIN TEST RUNNER ============

def run_all_tests():
    """Run all tests and generate report"""
    print(f"\n{BLUE}{'#'*60}{RESET}")
    print(f"{BLUE}#      ECHO V3 & V4 COMPREHENSIVE SYSTEM TEST{RESET}")
    print(f"{BLUE}#      Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'#'*60}{RESET}")

    results = {
        "V3 Database": test_v3_database(),
        "V3 Embeddings": test_v3_embeddings(),
        "V3 LLM Client": test_v3_llm_client(),
        "V3 Config": test_v3_config(),
        "V4 Partner Brain": test_v4_partner_brain(),
        "V4 Telemetry": test_v4_telemetry(),
        "V4 Orchestrator": test_v4_orchestrator(),
        "V4 HRM Model": test_v4_hrm_model(),
        "V4 Hunter Epoch": test_v4_hunter_epoch(),
        "V4 Monitor": test_v4_monitor(),
        "File Structure": test_file_structure(),
        "HRM Weights": test_hrm_weights(),
        "Database Integrity": test_database_integrity(),
    }

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results.values())
    total = len(results)
    percentage = (passed / total) * 100

    for test_name, passed in results.items():
        status = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
        print(f"{status} {test_name}")

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}FINAL RESULT: {passed}/{total} tests passed ({percentage:.1f}%){RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    if percentage == 100:
        print(f"{GREEN}🎉 ALL SYSTEMS OPERATIONAL!{RESET}")
    elif percentage >= 80:
        print(f"{YELLOW}⚠️  Most systems operational, some issues detected{RESET}")
    else:
        print(f"{RED}🚨 CRITICAL SYSTEMS FAILURE - Immediate attention required{RESET}")

    return percentage == 100

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}FATAL ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)