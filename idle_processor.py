"""
MODULE 4: THE RESOURCE ORCHESTRATOR (idle_processor.py)
Role: Protection of Latency.
- Monitors Mixing Apps (Serato, Resolume).
- Pauses AI (SIGSTOP) when mixing.
- Resumes AI (SIGCONT) when idle.
"""
import time
import os
import subprocess
import logging
import signal

logger = logging.getLogger("ResourceGuard")

CRITICAL_PROCESSES = ["Serato DJ Pro", "Resolume Arena", "Ableton Live"]
AI_WORKER_NAMES = ["v4_orchestrator.py", "partner_brain.py", "listener_daemon.py"] 
# Note: listener_daemon requires low cpu, maybe we don't pause hearing, just thinking.

class ResourceGuard:
    def __init__(self):
        self.paused = False

    def check_critical_processes(self):
        try:
            # grep -v grep prevents matching the grepping process itself
            cmd = f"ps aux | grep -v grep | grep -E '{'|'.join(CRITICAL_PROCESSES)}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return len(result.stdout.strip()) > 0
        except Exception as e:
            logger.error(f"Process check failed: {e}")
            return False

    def manage_resources(self):
        is_busy = self.check_critical_processes()

        if is_busy and not self.paused:
            logger.warning("🚨 CRITICAL APP DETECTED. PAUSING AI...")
            self.pause_ai()
            self.paused = True
        elif not is_busy and self.paused:
            logger.info("✅ System Idle. Resuming AI...")
            self.resume_ai()
            self.paused = False

    def pause_ai(self):
        # Find PIDs of heavy AI workers
        for proc_name in AI_WORKER_NAMES:
            self._signal_process(proc_name, signal.SIGSTOP)

    def resume_ai(self):
        for proc_name in AI_WORKER_NAMES:
            self._signal_process(proc_name, signal.SIGCONT)

    def _signal_process(self, proc_name, sig):
        try:
            # pkill -SIGNAME -f Pattern
            # Use strict matching to avoid killing benign things with similar names
            subprocess.run(["pkill", f"-{int(sig)}", "-f", proc_name], check=False)
        except Exception as e:
            logger.error(f"Failed to signal {proc_name}: {e}")

if __name__ == "__main__":
    guard = ResourceGuard()
    logging.basicConfig(level=logging.INFO)
    logger.info("Resource Guard Active. Monitoring...")
    while True:
        guard.manage_resources()
        time.sleep(5)
