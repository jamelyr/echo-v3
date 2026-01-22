
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
    
    def __init__(self, model_name: str = "Llama-3.2-3B-Instruct-4bit"):
        # Setup Model Connection to Local Server
        # Defaulting to 127.0.0.1:1234 (Echo V3 standard)
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBILITY_MODEL,
            model_type=model_name,
            model_config_dict={
                "temperature": 0.0,
                "max_tokens": 16384 # support complex reasoning/summaries
            },
            url="http://127.0.0.1:1234/v1",
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
Your goal is to fulfill user requests by browsing the web effectively.

CORE CAPABILITIES:
1. `search(query: str)`: Search DuckDuckGo for the specified query.
2. `navigate(url: str, wait: str = 'load')`: Navigate to a specific URL.
3. `click(selector: str)`: Click an element using its tag (e.g., 'n123').
4. `type_text(selector: str, text: str)`: Type text into a field (e.g., 'n456').
5. `snapshot(view: str = 'a11y', interactive_only: bool = True, limit: int = 150)`: View the current page state.

TOOL CALLING FORMAT:
You MUST provide exactly ONE tool call per turn using this XML format:
<tool_call>
{"name": "search", "parameters": {"query": "Hacker News top post"}}
</tool_call>

STRATEGY:
- Start by searching if you don't have a direct URL.
- Use `snapshot` to see the results and find element tags like `[n12]`.
- To open a link, use `click('n12')` where `n12` is the link's tag.
- Work step-by-step. Think clearly about your next move before calling a tool.
- If you have the final answer, start your response with "Answer:".

EXAMPLE WORKFLOW:
Thought: I need to find the top post on HN.
<tool_call>
{"name": "navigate", "parameters": {"url": "https://news.ycombinator.com"}}
</tool_call>
Observation: Snapshot shows `[n1] Title of Post (author)`.
Thought: I found the top post.
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
