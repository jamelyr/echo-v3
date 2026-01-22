"""
Echo V4 Configuration
"""
import os

# --- Paths ---
HOME = os.path.expanduser("~")
ECHO_ROOT = os.path.join(HOME, "echo")
RAW_AUDIO_DIR = os.path.join(ECHO_ROOT, "raw")
STAGING_DIR = os.path.join(ECHO_ROOT, "staging")
ARCHIVE_DIR = os.path.join(ECHO_ROOT, "archive")
DB_PATH = os.path.join(ECHO_ROOT, "db", "golden_ball_ledger.db")

# --- Resource Guard ---
# If any of these processes are running, the Orchestrator will PAUSE.
CRITICAL_PROCESSES = [
    "Serato DJ Pro",
    "Resolume Arena",
    "Ableton Live",
    "Logic Pro X"
]

# --- AI Models ---
# Placeholders for now - swap with real paths when models are downloaded.
NOVASR_PATH = os.path.join(ECHO_ROOT, "models", "novasr_52k.bin")
SAPIENT_HRM_PATH = os.path.join(HOME, "Documents", "ag", "HRM", "sapient_hrm_arc2.bin")
HUNTER_EPOCH_RULES_PATH = os.path.join(HOME, "Documents", "ag", "v4", "config", "hunter_epoch_rules.json")
WHISPER_MODEL = "large-v3"

# --- Thresholds ---
MAX_MEMORY_USAGE_GB = 12.0  # Orchestrator will try to stay below this system-wide
POLL_INTERVAL_SECONDS = 5.0
