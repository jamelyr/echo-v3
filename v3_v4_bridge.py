#!/usr/bin/env python3
"""
V3 + V4 Bridge Module
Routes decisions between HRM (V4) and LLM (V3) based on task type
Aggregates confidence scores from both models
"""
import logging
import asyncio
from typing import Dict, Any, Optional
import database
import llm_client

logger = logging.getLogger("V3V4Bridge")

class V3V4Bridge:
    """
    Bridges V3 LLM and V4 HRM models
    Routes tasks to appropriate reasoning engine based on type and confidence
    """
    
    def __init__(self, partner_brain=None):
        """
        Initialize bridge
        
        Args:
            partner_brain: PartnerBrain instance (optional, for HRM pattern matching)
        """
        self.partner_brain = partner_brain
        self.v3_llm = llm_client
        
        # Pattern matching keywords (HRM's strength)
        self.pattern_keywords = [
            'complete', 'pattern', 'sequence', 'series',
            'next', 'continues', 'follows', 'find',
            'puzzle', 'riddle', 'solve',
            'match', 'sort', 'arrange'
        ]
        
        # General reasoning keywords (V3's strength)
        self.general_keywords = [
            'why', 'how', 'explain', 'reason',
            'should', 'could', 'would',
            'recommend', 'suggest', 'advice',
            'create', 'design', 'plan',
            'analyze', 'evaluate', 'compare'
        ]
    
    def classify_task(self, description: str) -> str:
        """
        Classify task as pattern-matching or general reasoning
        
        Args:
            description: Task description
        
        Returns:
            'pattern' or 'general'
        """
        desc_lower = description.lower()
        
        pattern_score = sum(1 for kw in self.pattern_keywords if kw in desc_lower)
        general_score = sum(1 for kw in self.general_keywords if kw in desc_lower)
        
        # Also check length - longer tasks need general reasoning
        if len(description.split()) > 10:
            general_score += 2
        
        if pattern_score > general_score:
            logger.info(f"Task classified as PATTERN (score: {pattern_score} vs {general_score})")
            return 'pattern'
        else:
            logger.info(f"Task classified as GENERAL (score: {general_score} vs {pattern_score})")
            return 'general'
    
    def reason_with_confidence(self, description: str, context: str = "") -> Dict[str, Any]:
        """
        Route and execute reasoning with confidence tracking
        
        Args:
            description: Task description
            context: Additional context (optional)
        
        Returns:
            {
                'answer': str,
                'confidence': float (0-1),
                'source': 'V3' or 'V4-HRM',
                'reasoning_trace': list,
                'task_type': 'general' or 'pattern'
            }
        """
        task_type = self.classify_task(description)
        
        # Route to appropriate model
        if task_type == 'pattern' and self.partner_brain and self.partner_brain.hrm_loaded:
            return self._route_to_hrm(description, context)
        else:
            return self._route_to_v3(description, context)
    
    def _route_to_hrm(self, description: str, context: str) -> Dict[str, Any]:
        """
        Route pattern-matching task to V4 HRM
        
        Args:
            description: Task description
            context: Additional context
        
        Returns:
            HRM response with confidence tracking
        """
        logger.info(f"Routing to V4 HRM: {description}")
        
        try:
            # Encode task description
            if self.partner_brain and self.partner_brain.rule_encoder:
                task_embedding = self.partner_brain.rule_encoder.encode([description])
            else:
                logger.warning("Rule encoder not available, using V3 fallback")
                return self._route_to_v3(description, context)
            
            # For now, return pattern recognition response
            # In full implementation, this would call HRM forward pass
            answer = f"Pattern recognition: {description}"
            confidence = 0.6  # HRM is moderate confidence without fine-tuning
            
            logger.info(f"HRM response: {answer} (confidence: {confidence})")
            
            return {
                'answer': answer,
                'confidence': confidence,
                'source': 'V4-HRM',
                'reasoning_trace': ['Pattern detection', 'Rule matching'],
                'task_type': 'pattern'
            }
            
        except Exception as e:
            logger.error(f"HRM processing failed: {e}")
            # Fallback to V3
            return self._route_to_v3(description, context)
    
    def _route_to_v3(self, description: str, context: str) -> Dict[str, Any]:
        """
        Route general reasoning task to V3 LLM
        
        Args:
            description: Task description
            context: Additional context
        
        Returns:
            V3 LLM response with confidence tracking
        """
        logger.info(f"Routing to V3 LLM: {description}")
        
        try:
            # Build prompt for V3 LLM
            if context:
                prompt = f"Context: {context}\n\nTask: {description}\n\nPlease provide a solution with confidence score (0-1)."
            else:
                prompt = f"Task: {description}\n\nPlease provide a solution with confidence score (0-1)."
            
            # Call V3 LLM (using existing fast paths where possible)
            # First, check if it's a task operation (fast path)
            if any(kw in description.lower() for kw in ['add task', 'complete task', 'list tasks', 'delete task']):
                # Use direct database operations
                if 'add task' in description.lower():
                    task_desc = description.replace('add task', '').strip()
                    if not task_desc:
                        task_desc = description
                    task_id = database.add_task(task_desc)
                    answer = f"Task added with ID: {task_id}"
                    confidence = 1.0  # Direct DB op is certain
                    trace = ['Database add_task', f'Task ID: {task_id}']
                
                elif 'list tasks' in description.lower():
                    tasks = database.get_tasks()
                    answer = f"Found {len(tasks)} tasks"
                    for task in tasks[:5]:  # Show first 5
                        answer += f"\n  - {task['description']}"
                    confidence = 1.0
                    trace = ['Database get_tasks']
                
                elif 'complete task' in description.lower():
                    task_desc = description.replace('complete task', '').strip()
                    result = database.complete_task_by_description(task_desc)
                    if result:
                        answer = f"Task completed: {result['description']}"
                        confidence = 1.0
                        trace = ['Database complete_task', f'Task ID: {result["id"]}']
                    else:
                        answer = f"Task not found: {task_desc}"
                        confidence = 0.0
                        trace = ['Database lookup failed']
                
                else:
                    # Default to general LLM
                    answer = self._call_llm_general(prompt)
                    confidence = 0.7
                    trace = ['V3 LLM inference']
            
            else:
                # General LLM call
                answer = self._call_llm_general(prompt)
                confidence = 0.7
                trace = ['V3 LLM inference']
            
            logger.info(f"V3 response: {answer[:100]}... (confidence: {confidence})")
            
            return {
                'answer': answer,
                'confidence': confidence,
                'source': 'V3-LLM',
                'reasoning_trace': trace,
                'task_type': 'general'
            }
            
        except Exception as e:
            logger.error(f"V3 processing failed: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'confidence': 0.0,
                'source': 'ERROR',
                'reasoning_trace': [f'Error: {e}'],
                'task_type': 'unknown'
            }
    
    def _call_llm_general(self, prompt: str) -> str:
        """
        Call V3 LLM for general inference
        
        Args:
            prompt: The prompt to send to LLM
        
        Returns:
            LLM response text
        """
        # Import here to avoid circular dependency
        import llm_client as llm
        
        # Check if MLX server is running
        try:
            # Run async function in sync context
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                llm.process_input(prompt, history=[])
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Could not connect to LLM server: {str(e)}"
    
    def aggregate_confidence(self, hrm_result: Dict, v3_result: Dict) -> Dict[str, Any]:
        """
        Aggregate confidence from both models
        
        Args:
            hrm_result: Result from HRM model
            v3_result: Result from V3 LLM
        
        Returns:
            Aggregated result with combined confidence
        """
        hrm_conf = hrm_result.get('confidence', 0.0)
        v3_conf = v3_result.get('confidence', 0.0)
        
        # Weight toward V3 for general reasoning, HRM for patterns
        hrm_weight = 0.4 if v3_result.get('task_type') == 'general' else 0.7
        v3_weight = 1.0 - hrm_weight
        
        combined_conf = (hrm_weight * hrm_conf) + (v3_weight * v3_conf)
        
        # Choose answer from higher confidence source
        final_answer = v3_result['answer'] if v3_conf > hrm_conf else hrm_result['answer']
        final_source = 'V3-LLM' if v3_conf > hrm_conf else 'V4-HRM'
        
        return {
            'answer': final_answer,
            'confidence': combined_conf,
            'hrm_confidence': hrm_conf,
            'v3_confidence': v3_conf,
            'source': final_source,
            'reasoning_trace': [
                f'HRM confidence: {hrm_conf:.2f}',
                f'V3 confidence: {v3_conf:.2f}',
                f'Combined: {combined_conf:.2f}',
                f'Selected: {final_source}'
            ]
        }
    
    def route_with_verification(self, description: str, context: str = "", require_verification: bool = False) -> Dict[str, Any]:
        """
        Route with optional verification for high-stakes decisions
        
        Args:
            description: Task description
            context: Additional context
            require_verification: If True, require manual verification for low confidence
        
        Returns:
            Decision with verification flag
        """
        result = self.reason_with_confidence(description, context)
        
        # Add verification flag for low confidence
        result['requires_verification'] = (
            require_verification and 
            result['confidence'] < 0.7
        )
        
        if result['requires_verification']:
            result['answer'] += "\n\n⚠️ LOW CONFIDENCE: Manual verification recommended."
            logger.warning(f"Low confidence decision ({result['confidence']:.2f}), requires verification")
        
        return result


# Singleton instance for easy access
_bridge_instance: Optional[V3V4Bridge] = None

def get_bridge(partner_brain=None) -> V3V4Bridge:
    """
    Get singleton bridge instance
    
    Args:
        partner_brain: PartnerBrain instance (optional)
    
    Returns:
        V3V4Bridge instance
    """
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = V3V4Bridge(partner_brain)
    return _bridge_instance


if __name__ == "__main__":
    # Test bridge
    logging.basicConfig(level=logging.INFO)
    
    bridge = get_bridge()
    
    # Test pattern matching task
    print("\n=== Test 1: Pattern Matching ===")
    result1 = bridge.reason_with_confidence("Complete the pattern: 1, 2, 3, ?")
    print(f"Answer: {result1['answer']}")
    print(f"Confidence: {result1['confidence']:.2f}")
    print(f"Source: {result1['source']}")
    
    # Test general reasoning task
    print("\n=== Test 2: General Reasoning ===")
    result2 = bridge.reason_with_confidence("What should I buy for dinner? Consider healthy options.")
    print(f"Answer: {result2['answer'][:200]}...")
    print(f"Confidence: {result2['confidence']:.2f}")
    print(f"Source: {result2['source']}")
    
    # Test confidence aggregation
    print("\n=== Test 3: Confidence Aggregation ===")
    aggregated = bridge.aggregate_confidence(result1, result2)
    print(f"Combined: {aggregated['confidence']:.2f}")
    print(f"Source: {aggregated['source']}")
    
    # Test with verification
    print("\n=== Test 4: With Verification ===")
    result3 = bridge.route_with_verification("Make a major financial decision", require_verification=True)
    print(f"Requires verification: {result3['requires_verification']}")
    print(f"Confidence: {result3['confidence']:.2f}")