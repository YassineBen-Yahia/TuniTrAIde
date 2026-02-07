from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List, Optional, TypedDict
from dotenv import load_dotenv
import os
import json
load_dotenv()
from langchain_ollama import ChatOllama


model_kwargs = {
    "model": os.getenv("OLLAMA_MODEL"),
    "base_url": os.getenv("OLLAMA_BASE_URL")
}
if os.getenv("OLLAMA_API_KEY"):
    model_kwargs["headers"] = {
        'Authorization': f'Bearer {os.getenv("OLLAMA_API_KEY")}'
    }
llm = ChatOllama(**model_kwargs)


class AgentState(TypedDict):
    current_step: str
    query: str
    user_id: str
    intention : str
    symbols: List[str]
    rationale: Optional[str]
    comparison: Optional[str]
    reccommendation: Optional[str]



intentions = [
    "INVESTMENT_ADVICE",
    "MARKET_ANALYSIS",
    "COMPARATIVE_ANALYSIS",
    "PORTFOLIO_ADVICE",
    "OTHER"
]



def identify_intention_node(state: AgentState) -> AgentState:
   """Detect if user wants to generate questions or answer questions."""
   
   query = state["query"].lower()
   prompt=f"""You are an intent classification agent for a financial chatbot.

Your job is to read a user message and classify it into ONE of the following intents:

- INVESTMENT_ADVICE
- MARKET_ANALYSIS
- COMPARATIVE_ANALYSIS
- PORTFOLIO_ADVICE
- OTHER

Return ONLY the intent label.
Do not explain.
Do not output anything else.
Example:
user: "Should I buy AAPL stock?"
response: INVESTMENT_ADVICE
user: "Can you analyze the market trends for AAPL and MSFT?"
response: MARKET_ANALYSIS
user: "what should I invest in given my risk profile?"
response: INVESTMENT_ADVICE
user: "Given my portfolio, how should I allocate my assets?"
response: PORTFOLIO_ADVICE

if the user mentions his portfolio, or investment goals, classify as PORTFOLIO_ADVICE.

    user request: {query}
    intent:"""
   msg= HumanMessage(content=prompt)
   intent=llm.invoke([msg])
   intent_str= str(intent.content).strip() if not isinstance(intent, str) else intent
   if intent_str not in intentions:
       intent_str = "OTHER"

   print("Detected intent:", intent_str)
   return {
        **state,
        "intention": intent_str,
        "current_step": "intent_detected"
    }



