#!/usr/bin/env python3
"""
V3 LLM Wrapper (V3-V4 Bridge simplified)
Directly uses V3 LLM for all reasoning
No HRM, no routing needed
"""
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger("V3LLMWrapper")

class V3LLMWrapper:
    """
    Simple wrapper for V3 LLM
    All reasoning goes through V3 LLM
    """
    
    def __init__(self):
        logger.info("V3 LLM Wrapper initialized")
    
    def reason(self, description: str, context: str = "") -> Dict[str, Any]:
        """
        Send reasoning request to V3 LLM
        
        Args:
            description: Task/query description
            context: Additional context (optional)
        
        Returns:
            {
                'answer': str,
                'confidence': float (always 0.8 for V3),
                'source': 'V3-LLM'
            }
        """
        try:
            import llm_client
            
            # Build prompt
            if context:
                prompt = f"Context: {context}\n\nQuery: {description}"
            else:
                prompt = description
            
            # Call V3 LLM (async in sync context)
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                llm_client.process_input(prompt, user_id="wrapper", history=[])
            )
            
            logger.info(f"V3 LLM response: {response[:100]}...")
            
            return {
                'answer': response,
                'confidence': 0.8,  # V3 is consistently good
                'source': 'V3-LLM'
            }
            
        except Exception as e:
            logger.error(f"V3 LLM call failed: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'confidence': 0.0,
                'source': 'ERROR'
            }


# Singleton instance
_wrapper_instance = None

def get_wrapper() -> V3LLMWrapper:
    """Get singleton instance"""
    global _wrapper_instance
    if _wrapper_instance is None:
        _wrapper_instance = V3LLMWrapper()
    return _wrapper_instance


if __name__ == "__main__":
    import sys
    
    # Test
    wrapper = get_wrapper()
    
    test_queries = [
        "What should I buy for dinner?",
        "Add task: Complete the project",
        "Why is the sky blue?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        result = wrapper.reason(query)
        print(f"Source: {result['source']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Answer: {result['answer'][:200]}...")
