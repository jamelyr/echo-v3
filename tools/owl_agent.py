
import os
from typing import List, Optional
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.toolkits import OpenAIFunction
import tools.browser_tool as browser

class OWLAgent:
    """
    OWL (Official Web Learner) Browser Agent using CAMEL-AI.
    Controls a stateful browser via webctl and performs multi-step research.
    """
    
    def __init__(self, model_url: str = "http://127.0.0.1:8080/v1"):
        # Setup Model Connection to Echo's MLX Server
        # Uses the currently loaded hot-swappable model
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBILITY_MODEL,
            model_type="current",  # Will use whatever model is loaded
            model_config_dict={
                "temperature": 0.0,
                "max_tokens": 4096  # Conservative for RAM preservation
            },
            url=model_url,
            api_key="EMPTY"
        )
        
        # Define Browser Tools using OpenAIFunction
        self.tools = [
            OpenAIFunction(browser.navigate),
            OpenAIFunction(browser.search),
            OpenAIFunction(browser.click),
            OpenAIFunction(browser.type_text),
            OpenAIFunction(browser.scroll),
            OpenAIFunction(browser.snapshot)
        ]
        
# System Message
        sys_msg = BaseMessage.make_assistant_message(
            role_name="OWLAgent",
            content="""You are the OWL Browser Agent, an expert in web research and navigation.
Your goal is to fulfill user requests by browsing the web effectively using the current Echo model.

CORE CAPABILITIES:
1. `search(query: str)`: Search DuckDuckGo for the specified query.
2. `navigate(url: str, wait: str = 'load')`: Navigate to a specific URL.
3. `click(selector: str)`: Click an element using its tag (e.g., 'n123').
4. `type_text(selector: str, text: str)`: Type text into a field (e.g., 'n456').
5. `snapshot(view: str = 'a11y', interactive_only: bool = True, limit: int = 150)`: View the current page state.

IMPORTANT CONSTRAINTS:
- You are using Echo's current MLX model (hot-swappable)
- Be concise and efficient to preserve RAM
- Use exactly ONE tool call per turn
- Think step-by-step but keep reasoning brief

TOOL CALLING FORMAT:
You MUST provide exactly ONE tool call per turn using this XML format:
<tool_call>
{"name": "search", "parameters": {"query": "Hacker News top post"}}
 

STRATEGY:
- Start by searching if you don't have a direct URL.
- Use `snapshot` to see the results and find element tags like `[n12]`.
- To open a link, use `click('n12')` where `n12` is the link's tag.
- Work step-by-step. Keep thoughts brief.
- If you have the final answer, start your response with "Answer:".

EXAMPLE WORKFLOW:
Thought: Need top HN post.
<tool_call>
{"name": "navigate", "parameters": {"url": "https://news.ycombinator.com"}}
 
Observation: Snapshot shows `[n1] Title of Post (author)`.
Thought: Found top post.
Answer: The top post is "Title of Post" by author.
"""
        )
        
        self.agent = ChatAgent(
            system_message=sys_msg,
            model=self.model,
            tools=self.tools
        )
        
    def run_task(self, task: str, max_steps: int = 15) -> str:
        """
        Executes a browsing task using a multi-step loop.
        """
        # Ensure browser is ready
        browser.start_session(mode="unattended")
        
        user_msg = BaseMessage.make_user_message(role_name="User", content=task)
        
        print(f"🦉 OWL starting task: {task}")
        last_content = ""
        
        for i in range(max_steps):
            print(f"🤔 OWL Step {i+1}/{max_steps}...")
            
            # The ChatAgent.step() performs the ReAct loop INTERNALLY for one "turn".
            # If the model calls multiple tools in one turn, it handles them.
            # But it stops when the model outputs JUST text (no more tool calls).
            response = self.agent.step(user_msg)
            
            content = response.msg.content
            last_content = content
            
            # Log the thought/action
            if content:
                print(f"✨ OWL Thought: {content[:200]}...")
            
            # Check for final answer
            if "Answer:" in content:
                return content
            
            # If the agent is terminated according to CAMEL's logic
            if response.terminated:
                break
                
            # If no tools were called in this step and no answer provided, 
            # we might be at a dead end or the model just wants to explain.
            # We'll nudge it once if it hasn't given an answer.
            if not response.info.get('tool_calls'):
                if i < max_steps - 1:
                    print("⚠️ OWL provided no action. Nudging...")
                    user_msg = BaseMessage.make_user_message(
                        role_name="User", 
                        content="Please continue with the next logical step to find the answer. Use `snapshot` if you are unsure of the current page state. If you have the answer, start your response with 'Answer:'."
                    )
                    continue
                else:
                    break
            
            # If tools were called, the results are already in memory.
            # We need to tell the agent to keep going based on those results.
            user_msg = BaseMessage.make_user_message(
                role_name="User", 
                content="Proceed with the next step based on the tool results above."
            )

        return last_content

def run_owl_task(task: str) -> str:
    agent = OWLAgent()
    return agent.run_task(task)

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Find the current price of Bitcoin in USD."
    result = run_owl_task(query)
    print("\nFINAL RESULT:\n", result)
