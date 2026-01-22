
import json
import re
import time

def extract_all_json(text):
    """Greedily find all JSON-like blocks by balancing braces."""
    results = []
    start_indices = [i for i, char in enumerate(text) if char == '{']
    
    consumed_until = -1
    for start in start_indices:
        if start < consumed_until:
            continue
            
        stack = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    potential = text[start:i+1]
                    try:
                        json.loads(potential)
                        results.append(potential)
                        consumed_until = i + 1
                        break
                    except:
                        pass
    return results

def parse_tools(response_text, tools_list):
    message = {"role": "assistant", "content": response_text.strip()}
    tool_calls = []
    text = response_text.strip()
    
    # 1. Look for <tool_call> XML tags (Qwen format)
    xml_matches = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    print(f"DEBUG: xml_matches found: {len(xml_matches)}")
    for block in xml_matches:
        try:
            # Maybe there's a JSON inside the XML block?
            json_blocks = extract_all_json(block)
            data_str = json_blocks[0] if json_blocks else block.strip()
            tool_data = json.loads(data_str)
            if "name" in tool_data:
                name = tool_data["name"]
                args = tool_data.get("parameters") or tool_data.get("arguments") or {}
                
                # Heuristic Mapping
                if isinstance(args, dict) and "arg1" in args and len(args) == 1:
                    if name == "search": args = {"query": args["arg1"]}
                    elif name == "navigate": args = {"url": args["arg1"]}
                    elif name == "click": args = {"selector": args["arg1"]}
                    elif name == "snapshot": args = {"view": args["arg1"]}
                
                tool_calls.append({
                    "id": f"call_{int(time.time())}_{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args) if not isinstance(args, str) else args
                    }
                })
        except Exception as e:
            print(f"DEBUG: XML Tool parse error: {e}")
            continue
    
    # 2. Look for raw JSON blocks if no XML matches found (Llama format)
    if not tool_calls:
        json_blocks = extract_all_json(text)
        print(f"DEBUG: potential_json found: {len(json_blocks)}")
        for block in json_blocks:
            try:
                tool_data = json.loads(block)
                if "name" in tool_data and ("parameters" in tool_data or "arguments" in tool_data):
                    name = tool_data["name"]
                    args = tool_data.get("parameters") or tool_data.get("arguments")
                    
                    # Heuristic Mapping
                    if isinstance(args, dict) and "arg1" in args and len(args) == 1:
                        if name == "search": args = {"query": args["arg1"]}
                        elif name == "navigate": args = {"url": args["arg1"]}
                        elif name == "click": args = {"selector": args["arg1"]}
                    
                    tool_calls.append({
                        "id": f"call_{int(time.time())}_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args) if not isinstance(args, str) else args
                        }
                    })
            except Exception as e:
                print(f"DEBUG: JSON Tool parse error: {e}")
                continue
    
    if tool_calls:
        print(f"DEBUG: Found {len(tool_calls)} tool calls")
        message["tool_calls"] = tool_calls
        message["content"] = None
    
    return message

# Test Cases
test_response_1 = """
I'll search for the current top post on Hacker News.
<tool_call>
{"name": "search", "parameters": {"query": "Hacker News top post"}}
</tool_call>
"""

test_response_2 = """
{"name": "navigate", "arguments": {"url": "https://news.ycombinator.com"}}
"""

test_response_3 = """
I'll check the page and then search.
<tool_call>{"name": "snapshot", "parameters": {"view": "a11y"}}</tool_call>
And then maybe:
{"name": "search", "arguments": {"query": "advanced ML techniques"}}
"""

print("--- Test 1 (XML/Qwen) ---")
res1 = parse_tools(test_response_1, [{}])
print(json.dumps(res1, indent=2))

print("\n--- Test 2 (JSON/Llama) ---")
res2 = parse_tools(test_response_2, [{}])
print(json.dumps(res2, indent=2))

print("\n--- Test 3 (Mixed/Multiple) ---")
res3 = parse_tools(test_response_3, [{}])
print(json.dumps(res3, indent=2))
