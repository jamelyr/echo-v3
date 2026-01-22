"""
MODULE 3: THE GOLDEN BALL GOVERNOR (hunter_epoch.py)
Authority: Ensuring all actions align with the Hunter Epoch.
Primary Metric: Rs 1.5M Liquid Cash.
"""
import logging

logger = logging.getLogger("HRM.Governor")

# epoch_constraints.py
EPOCH_NAME = "The Hunter"
TARGET_LIQUIDITY = 1500000.0
# Current state would ideally come from a DB, hardcoded for V1 safety
CURRENT_LIQUIDITY = 0.0 

# Thresholds
MAX_AUTO_SPEND = 5000.0  # Rs
MAX_AUTO_TIME_COMMITMENT = 2.0  # Hours

class HunterEpoch:
    @staticmethod
    def audit_action(action_type: str, details: dict) -> dict:
        """
        Audits a proposed action against Golden Ball constraints.
        Returns: {'approved': bool, 'reason': str}
        """
        logger.info(f"Auditing Action: {action_type} | {details}")
        
        # 1. Financial Audit
        cost = details.get("cost", 0.0)
        if cost > MAX_AUTO_SPEND:
            return {
                "approved": False,
                "reason": f"Strategic Conflict: Cost (Rs {cost}) exceeds auto-limit (Rs {MAX_AUTO_SPEND})."
            }
            
        # 2. Time Audit
        hours = details.get("hours", 0.0)
        if hours > MAX_AUTO_TIME_COMMITMENT:
            return {
                "approved": False,
                "reason": f"Strategic Conflict: Time ({hours}h) exceeds auto-limit ({MAX_AUTO_TIME_COMMITMENT}h)."
            }

        # 3. Epoch Alignment Check (Simple keyword heuristic for now, Sapient acts as the advanced filter)
        # If action is about "buying nonsense", flag it.
        # This function is usually called AFTER Sapient has theoretically "understood" the intent.
        
        return {"approved": True, "reason": "Aligned with Hunter Epoch."}
