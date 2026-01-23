#!/usr/bin/env python3
"""
Echo Auto Fact Extractor
Extracts entities, preferences, and facts from conversation history
Integrates with MLX LLM for local processing
"""

import os
import json
import asyncio
import httpx
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

import database
import mlx_embeddings

load_dotenv()

MLX_URL = "http://127.0.0.1:1234/v1"

# Fact types to extract
FACT_TYPES = {
    "entity": "Names, IDs, identifiers for people, systems, calendars, projects",
    "preference": "User preferences, configurations, settings, likes/dislikes",
    "tech_stack": "Technologies, frameworks, tools, languages mentioned",
    "pattern": "Recurring behaviors, workflows, habits, routines",
    "context": "Job roles, team structure, project details, domain knowledge"
}

# Test/debug keywords to skip extraction
SKIP_KEYWORDS = [
    "test", "debug", "example", "demo", "trial", "sample",
    "testing", "placeholder", "fake", "mock", "dummy"
]

# Extraction prompt template
EXTRACTION_PROMPT = """You are a fact extraction specialist. Analyze this conversation and extract important facts.

CONVERSATION:
{conversation}

Extract facts in these categories:
- entity: Names, IDs, identifiers (e.g., "Nirvan's calendar ID: cal-abc123", "Project Alpha")
- preference: User preferences (e.g., "Prefers Python over JavaScript", "Likes dark mode")
- tech_stack: Technologies/tools (e.g., "Uses MLX for embeddings", "React for frontend")
- pattern: Recurring behaviors (e.g., "Always runs tests before deployment")
- context: Job/role info (e.g., "Software engineer on support team")

Return ONLY valid JSON in this exact format:
[
    {{
        "type": "entity|preference|tech_stack|pattern|context",
        "value": "exact fact text from conversation",
        "confidence": 0.0-1.0
    }}
]

Rules:
- Extract ONLY facts explicitly stated or clearly implied
- Confidence 1.0 = explicit statement, 0.7 = implied, 0.5 = uncertain
- Maximum 10 most important facts
- Return [] if no important facts found
"""

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FactExtractor")


def should_skip_extraction(messages: List[Dict]) -> tuple[bool, str]:
    """
    Check if conversation contains test/debug keywords
    
    Returns:
        (should_skip, reason)
    """
    # Combine all message content
    full_text = " ".join([m.get('content', '').lower() for m in messages])
    
    # Check for skip keywords
    for keyword in SKIP_KEYWORDS:
        if keyword in full_text:
            return True, f"Contains '{keyword}' keyword"
    
    # Check if auto-extraction is disabled
    if os.getenv("AUTO_EXTRACT_FACTS", "true").lower() == "false":
        return True, "AUTO_EXTRACT_FACTS=false"
    
    return False, ""


async def extract_facts_from_messages(messages: List[Dict]) -> List[Dict]:
    """
    Extract facts from conversation using MLX LLM
    
    Args:
        messages: List of conversation messages with 'role' and 'content'
    
    Returns:
        List of extracted facts with {type, value, confidence}
    """
    if not messages:
        return []
    
    # Format conversation for LLM
    conversation_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages[-50:]  # Last 50 messages to avoid context overflow
    ])
    
    # Build prompt
    prompt = EXTRACTION_PROMPT.format(conversation=conversation_text)
    
    messages_for_llm = [
        {"role": "system", "content": "You are a JSON-only fact extractor. Return valid JSON arrays only."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MLX_URL}/chat/completions",
                json={
                    "messages": messages_for_llm,
                    "max_tokens": 800,
                    "temperature": 0.1
                }
            )
            
            if response.status_code != 200:
                logger.error(f"MLX API error: {response.status_code}")
                return []
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from response
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            facts = json.loads(content)
            
            # Validate and filter
            valid_facts = []
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                if fact.get("type") not in FACT_TYPES:
                    continue
                if not fact.get("value"):
                    continue
                
                # Ensure confidence is valid
                confidence = fact.get("confidence", 0.7)
                if not isinstance(confidence, (int, float)):
                    confidence = 0.7
                confidence = max(0.0, min(1.0, confidence))
                
                valid_facts.append({
                    "type": fact["type"],
                    "value": fact["value"],
                    "confidence": confidence
                })
            
            logger.info(f"Extracted {len(valid_facts)} facts")
            return valid_facts
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"Content: {content[:200]}...")
        return []
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return []


async def store_facts(extracted_facts: List[Dict], source: str = "chat_history") -> List[int]:
    """
    Store extracted facts in database with embeddings
    
    Args:
        extracted_facts: List of {type, value, confidence} dicts
        source: Source identifier (e.g., "chat_history", "archive_2024-01-23")
    
    Returns:
        List of fact IDs created
    """
    fact_ids = []
    
    for fact in extracted_facts:
        try:
            # Generate embedding for semantic search
            embedding = mlx_embeddings.get_embedding(fact["value"])
            
            # Store in database
            fact_id = database.add_fact(
                fact_type=fact["type"],
                value=fact["value"],
                confidence=fact["confidence"],
                source=source,
                metadata={"extracted_at": "auto"},
                embedding=embedding
            )
            
            fact_ids.append(fact_id)
            logger.debug(f"Stored fact {fact_id}: {fact['type']} - {fact['value'][:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
            continue
    
    logger.info(f"Stored {len(fact_ids)} facts in database")
    return fact_ids


async def extract_and_archive_facts(messages: List[Dict], archive_source: str = "session") -> Dict:
    """
    Main function: Extract facts from messages and store them
    
    Args:
        messages: Conversation messages
        archive_source: Source identifier for tracking
    
    Returns:
        {
            "skipped": bool,
            "reason": str,
            "extracted": int,
            "stored": int,
            "facts": List[Dict]
        }
    """
    result = {
        "skipped": False,
        "reason": "",
        "extracted": 0,
        "stored": 0,
        "facts": []
    }
    
    # Check if should skip
    should_skip, reason = should_skip_extraction(messages)
    if should_skip:
        result["skipped"] = True
        result["reason"] = reason
        logger.info(f"Skipping extraction: {reason}")
        return result
    
    # Extract facts
    logger.info(f"Extracting facts from {len(messages)} messages...")
    extracted_facts = await extract_facts_from_messages(messages)
    result["extracted"] = len(extracted_facts)
    result["facts"] = extracted_facts
    
    if not extracted_facts:
        logger.info("No facts extracted")
        return result
    
    # Store facts
    stored_ids = await store_facts(extracted_facts, source=archive_source)
    result["stored"] = len(stored_ids)
    
    return result


async def recall_facts(query: str, fact_type: str = None, limit: int = 5) -> str:
    """
    Recall relevant facts for a query
    
    Args:
        query: Search query
        fact_type: Optional filter by type (entity, preference, etc.)
        limit: Max results
    
    Returns:
        Formatted string of facts
    """
    # Generate embedding for query
    query_embedding = mlx_embeddings.get_embedding(query)
    
    if not query_embedding:
        return "❌ Could not generate embedding for query."
    
    # Search facts
    facts = database.get_similar_facts(
        query_embedding,
        fact_type=fact_type,
        top_k=limit
    )
    
    if not facts:
        return "No relevant facts found."
    
    # Format results
    result = f"Found {len(facts)} fact(s):\n"
    for i, fact in enumerate(facts, 1):
        result += f"{i}. [{fact['fact_type'].upper()}] {fact['value']}\n"
        result += f"   Confidence: {fact['confidence']:.2f} | Accessed: {fact.get('access_count', 0)} times\n"
        
        # Update access tracking
        database.update_fact_access(fact['id'])
    
    return result.strip()


# CLI entry point
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Echo Fact Extractor")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract facts from chat history")
    extract_parser.add_argument("--source", default="manual", help="Source identifier")
    
    # Recall command
    recall_parser = subparsers.add_parser("recall", help="Recall facts")
    recall_parser.add_argument("query", help="Search query")
    recall_parser.add_argument("--type", help="Filter by fact type")
    recall_parser.add_argument("--limit", type=int, default=5, help="Max results")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List stored facts")
    list_parser.add_argument("--type", help="Filter by fact type")
    list_parser.add_argument("--limit", type=int, default=20, help="Max results")
    
    args = parser.parse_args()
    
    # Initialize database
    database.init_db()
    
    if args.command == "extract":
        messages = database.get_all_chat_history()
        result = await extract_and_archive_facts(messages, source=args.source)
        
        print(f"\n{'='*60}")
        print("FACT EXTRACTION RESULTS")
        print(f"{'='*60}")
        print(f"Skipped: {result['skipped']}")
        print(f"Reason: {result['reason'] or 'N/A'}")
        print(f"Extracted: {result['extracted']}")
        print(f"Stored: {result['stored']}")
        
        if result['facts']:
            print(f"\n{'='*60}")
            print("EXTRACTED FACTS")
            print(f"{'='*60}")
            for i, fact in enumerate(result['facts'], 1):
                print(f"{i}. [{fact['type'].upper()}] {fact['value']}")
                print(f"   Confidence: {fact['confidence']:.2f}")
    
    elif args.command == "recall":
        result = await recall_facts(args.query, fact_type=args.type, limit=args.limit)
        print(result)
    
    elif args.command == "list":
        facts = database.get_facts(fact_type=args.type, limit=args.limit)
        
        print(f"\n{'='*60}")
        print("STORED FACTS")
        print(f"{'='*60}")
        
        if not facts:
            print("No facts stored.")
        else:
            for fact in facts:
                print(f"\n[{fact['fact_type'].upper()}] {fact['value']}")
                print(f"  Confidence: {fact['confidence']:.2f}")
                print(f"  Source: {fact.get('source', 'unknown')}")
                print(f"  Created: {fact['created_at']}")
                print(f"  Accessed: {fact.get('access_count', 0)} times")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())