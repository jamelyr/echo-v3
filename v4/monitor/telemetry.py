"""
Echo V4 Telemetry Module
Handles SharedMemory communication between partner_brain.py and v4_monitor.py.
"""
import json
import time
import logging
from multiprocessing import shared_memory

# Constants
SHARED_MEM_NAME = "echo_v4_telemetry"
SHARED_MEM_SIZE = 4096  # 4KB should be enough for our status JSON
DEFAULT_STATE = {
    "usage_id": "init",
    "timestamp": 0,
    "stage": "IDLE",            # INGEST, RESTORE, TRANSCRIBE, ENCODE, REASON, ACT
    "status": "IDLE",           # IDLE, ACTIVE, BLOCKED
    "metrics": {
        "kbps": 0,
        "latency_ms": 0,
        "word_confidence": 0.0,
        "vector_norm": 0.0,
        "act_steps": 0,            # Total steps for current thought
        "h_cycles": 0,             # High-level cycles
        "l_steps": 0               # Low-level steps
    },
    "alerts": [],               # List of alert strings e.g. ["SHALLOW REASONING"]
    "financial": {
        "cost": 0,
        "currency": "MUR",
        "conflict": False
    },
    "system": {
        "memory_resident": False
    }
}

class TelemetryWriter:
    """Writes brain state to shared memory."""
    def __init__(self):
        self.shm = None
        self._ensure_shm()

    def _ensure_shm(self):
        """Creates or attaches to the shared memory block."""
        try:
            # Try to create
            self.shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME, create=True, size=SHARED_MEM_SIZE)
            self._write_raw(DEFAULT_STATE)
        except FileExistsError:
            # Attach if existing
            self.shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME)
        except Exception as e:
            logging.error(f"Telemetry Init Failed: {e}")

    def _write_raw(self, state_dict):
        if not self.shm: return
        try:
            data = json.dumps(state_dict).encode('utf-8')
            if len(data) > SHARED_MEM_SIZE:
                logging.warning("Telemetry data too large, truncating!")
                data = data[:SHARED_MEM_SIZE]
            
            # Write length header? Simpler: Just write and rely on null termination or fill with spaces
            # Use a fixed buffer - fill rest with spaces to overwrite old data
            padded = data + b' ' * (SHARED_MEM_SIZE - len(data))
            self.shm.buf[:SHARED_MEM_SIZE] = padded
        except Exception as e:
            logging.error(f"Telemetry Write Error: {e}")

    def update(self, **kwargs):
        """Update specific fields in the telemetry state."""
        current = self.read() # Read current to merge
        
        # Deep merge helper or just simple top-level updates
        # For this usage, top-level keys + simple nested dict updates
        for k, v in kwargs.items():
            if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                current[k].update(v)
            else:
                current[k] = v
        
        current['timestamp'] = time.time()
        self._write_raw(current)

    def read(self):
        """Read current state (mostly to merge updates)."""
        if not self.shm: return DEFAULT_STATE.copy()
        try:
            # Read bytes until null or end usually, but we padded with spaces
            raw = bytes(self.shm.buf[:]).strip()
            # If empty (init race condition), return default
            if not raw: return DEFAULT_STATE.copy()
            # Find the null terminator if any (though we used spaces)
            return json.loads(raw.decode('utf-8').rstrip('\x00'))
        except Exception:
            return DEFAULT_STATE.copy()

    def close(self):
        if self.shm:
            self.shm.close()
            # Note: unlink() should only be called by a cleanup process or the last user.
            # We'll leave it persisting for the monitor.


class TelemetryReader:
    """Reads brain state from shared memory."""
    def __init__(self):
        self.shm = None
        self.connect()

    def connect(self):
        try:
            self.shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME)
        except FileNotFoundError:
            self.shm = None # Brain not started yet?

    def read(self):
        if not self.shm:
            self.connect()
            if not self.shm: return DEFAULT_STATE.copy()
        
        try:
            raw = bytes(self.shm.buf[:]).strip()
            if not raw: return DEFAULT_STATE.copy()
            state = json.loads(raw.decode('utf-8').rstrip('\x00'))
            return state
        except Exception:
            return DEFAULT_STATE.copy()

    def close(self):
        if self.shm:
            self.shm.close()
