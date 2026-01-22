
import time
import random
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v4.monitor.telemetry import TelemetryWriter

def simulate_brain():
    print("Initializing Telemetry Driver...")
    telemetry = TelemetryWriter()
    
    stages = ["INGEST", "RESTORE", "TRANSCRIBE", "ENCODE", "REASON", "ACT"]
    
    try:
        while True:
            # 1. Idle
            print("State: IDLE")
            telemetry.update(stage="IDLE", status="IDLE", metrics={"kbps": 0})
            time.sleep(2)
            
            # 2. Ingest
            print("State: INGEST")
            telemetry.update(stage="INGEST", status="ACTIVE", metrics={"kbps": 128})
            time.sleep(1)
            
            # 3. Transcribe
            print("State: TRANSCRIBE")
            telemetry.update(stage="TRANSCRIBE", metrics={"word_confidence": 0.85})
            time.sleep(1)
            
            # 4. Reason (HRM)
            print("State: REASON")
            telemetry.update(stage="REASON", status="ACTIVE")
            for i in range(1, 6):
                telemetry.update(metrics={"act_steps": i, "h_cycles": 1, "l_steps": i})
                time.sleep(0.5)
            
            # 5. Act (Financial Trigger)
            print("State: ACT (High Cost)")
            telemetry.update(stage="ACT", status="AUDITING", financial={"cost": 6000})
            time.sleep(1)
            
            # 6. Blocked
            print("State: BLOCKED")
            telemetry.update(status="BLOCKED", alerts=["STRATEGIC CONFLICT"])
            time.sleep(3)
            
            # Reset
            print("Resetting...")
            telemetry.update(
                stage="IDLE", 
                status="IDLE", 
                financial={"cost": 0}, 
                alerts=[],
                metrics={"act_steps": 0}
            )
            time.sleep(2)

    except KeyboardInterrupt:
        print("Driver Stopped.")

if __name__ == "__main__":
    simulate_brain()
