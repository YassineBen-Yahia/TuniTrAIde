import os
import json
import typing
from typing import TypedDict

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START

from agent.utils import get_symbols, get_last_days, format_market_data_summary
from agent.prompts.Investment import (
    INVESTMENT_PROMPT,
    INVESTMENT_PROMPT_V2,
    COMPARE_STOCK_PROMPT,
    ANALYSIS_PROMPT, 
    create_investment_prompt,
    advice_prompt_without_symbol
)
from agent.prompts.portfolio import PORTFOLIO_PROMPT, portfolio_advice_prompt

# --- Configuration & Setup ---

load_dotenv()

symbols = get_symbols("data/historical_data.csv")

model_kwargs = {
    "model": os.getenv("OLLAMA_MODEL"),
    "base_url": os.getenv("OLLAMA_BASE_URL")
}
if os.getenv("OLLAMA_API_KEY"):
    model_kwargs["headers"] = {
        'Authorization': f'Bearer {os.getenv("OLLAMA_API_KEY")}'
    }
llm = ChatOllama(**model_kwargs)

intentions = ["INVESTMENT_ADVICE", "MARKET_ANALYSIS", "COMPARATIVE_ANALYSIS", "OTHER", "PORTFOLIO_ADVICE"]

class AgentState(TypedDict):
    current_step: str
    query: str
    user_id: str
    intention : str
    stock_symbol: list[str]
    recommendation: str
    rationale: str
    comparison: str

# --- Node Functions ---

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

def identify_stock_node(state: AgentState) -> AgentState:
    """Identify stock symbols mentioned in the user query."""
    
    query = state["query"]
    prompt=f"""You are a stock symbol extraction agent for a financial chatbot.
Your job is to read a user message and extract all stock symbols mentioned.
If the stock symbol(s) mentioned are the in the following list, return them as a JSON array of strings with the same naming and casing in the list.
Here is the list of valid stock symbols:
{json.dumps(symbols)}
The user may mention multiple stock symbols. and they may use different casings.
If no valid stock symbols are mentioned, return an empty JSON array.    
If the user does not mention any stock symbols, return an empty JSON array.
If the user mentions a symbol that is not in the list, return this JSON array: ["no symbol"]
example:
user: "What do you think about SFBT and BT?"
response: ["SFBT", "BT"]
user: "What do you think about APPL?"
response: ["no symbol"]    
user: "What do you think about APPL and SFBT?"
response: ["no symbol", "SFBT"]     
user: "What do you think I should invest in?"
response: [] 
user: "What stocks should I invest in?"
response: []       
Return a JSON array of stock symbols.
    user request: {query}
    stock_symbols:"""
    msg= HumanMessage(content=prompt)
    response=llm.invoke([msg])
    print("Extracted stock symbols:", response)
    try:
        llm_symbols = json.loads(response.content)
        if not isinstance(llm_symbols, list):
            llm_symbols = []
    except json.JSONDecodeError:
        llm_symbols = []
    stock_symbol = llm_symbols if llm_symbols else []
    return {
        **state,
        "stock_symbol": stock_symbol,
        "current_step": "stock_identified"
    }

def investment_decision_node(state: AgentState) -> AgentState:
    """Make investment decision based on user profile and stock data."""
    
    user_id = state["user_id"]
    user_id = str(user_id)


    if len(state["stock_symbol"]) == 0:

        prompt = advice_prompt_without_symbol( user_id)
        msgs= [SystemMessage(content=INVESTMENT_PROMPT_V2),HumanMessage(content=prompt)]
        
        #with open('debug_investment_prompt.txt', 'w') as f:
        #    f.write(prompt+'\n'+'---END OF PROMPT---\n')
        response = llm.invoke(msgs)
    elif state["stock_symbol"][0] == "no symbol":
        prompt = """
        You are a financial advisor. The user is asking for investment advice but has specified stock symbols that are not in the list of valid stock symbols   .
        Mention that the stock symbols are not valid and ask the user to provide another stock symbol.
        Return the response as a JSON object with the following format:
        {
            "recommendation": "hold",
            "rationale": "explain that the list of stock symbols is not valid and ask the user to provide another stock symbol"
        }   
        """
        msgs= [SystemMessage(content=prompt),HumanMessage(content=state["query"])]
        
        #with open('debug_investment_prompt.txt', 'w') as f:
        #    f.write(prompt+'\n'+'---END OF PROMPT---\n')
        response = llm.invoke(msgs)
    else    :
        stock_symbol = state["stock_symbol"][0] # extracted from query

        prompt = create_investment_prompt(user_id, stock_symbol)

        with open('logs/debug_investment_prompt.txt', 'w') as f:
            f.write(prompt+'\n'+'---END OF PROMPT---\n'+stock_symbol+'\n'+user_id)

        
        messages= [
            SystemMessage(content=INVESTMENT_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
    
    # Parse the JSON response
    try:
        decision_data = json.loads(response.content)
        recommendation = decision_data.get("recommendation", "hold")
        rationale = decision_data.get("rationale", "")
    except json.JSONDecodeError:
        recommendation = "hold"
        rationale = "Could not parse response."
    
    return {
        **state,
        "recommendation": recommendation,
        "rationale": rationale,
        "current_step": "decision_made"
    }


def compare_stock_node(state: AgentState) -> AgentState:
    """Compare multiple stocks based on user query."""
    stocks = state["stock_symbol"]  # already a list of symbols
    data = get_last_days("data/historical_data.csv", 5)
    msgs= [SystemMessage(content=COMPARE_STOCK_PROMPT)]
    stocks_dict = {}
    for stock in stocks:
        stock_data = data[data['VALEUR'].astype(str).str.strip() == stock].tail(5)
        stock_data = format_market_data_summary(stock_data)
        stocks_dict[stock] = stock_data
    with open('logs/debug_compare_stocks_prompt.txt', 'w') as f:
        f.write(json.dumps(stocks_dict, indent=2))
    prompt=f"""Compare the stock {stocks} based on the following recent data:
{json.dumps(stocks_dict, indent=2)}
Provide a brief analysis of its performance and outlook."""
    
    msgs.append(HumanMessage(content=prompt))
    response = llm.invoke(msgs)
    return {
        **state,
        "comparison": str(response.content),
        "current_step": "stocks_compared"
    }

def market_analysis_node(state: AgentState) -> AgentState:
    print("market_analysis_node called")
    """Perform market analysis (placeholder)."""
    # Placeholder implementation
    data = get_last_days("data/historical_data.csv", 5)
    formatted_data = format_market_data_summary(data)
    msgs= [SystemMessage(content=ANALYSIS_PROMPT)]
    prompt=f"""Analyze the market based on the following recent data:

-------------------------

{formatted_data}
Provide a brief analysis of market trends and outlook."""
    with open('logs/debug_market_analysis_prompt.txt', 'w') as f:
        f.write(prompt)
    msgs.append(HumanMessage(content=prompt))
    response = llm.invoke(msgs)
    analysis = str(response.content)
    return {
        **state,
        "rationale": analysis,
        "current_step": "market_analyzed"
    }


def conversation_end_node(state: AgentState) -> AgentState:
    """End the conversation."""
    prompt=f"""
    you are an expert financial analyst.
    answer the user's query based with general information, investment decision, stock comparison, and market analysis.
    your answer should be concise and informative.
    do not exceed 100 words.
    do not reference any data points or external sources.

    user query: {state['query']}
    """
    msg= HumanMessage(content=prompt)
    response=llm.invoke([msg])

    return {
        **state,
        "rationale": str(response.content),
        "current_step": "end"
    }


def portfolio_advice_node(state: AgentState) -> AgentState:
    """Provide portfolio advice based on user profile."""
    user_id = state["user_id"]
    user_id = str(user_id)
    prompt = portfolio_advice_prompt(user_id, state["query"])
    msgs= [SystemMessage(content=PORTFOLIO_PROMPT),HumanMessage(content=prompt)]
    response = llm.invoke(msgs)
    try:
        advice_data = json.loads(response.content)
        recommendation = advice_data.get("recommendation", "")
        rationale = advice_data.get("rationale", "")
    except json.JSONDecodeError:
        recommendation = ""
        rationale = "Could not parse response."
    return {
        **state,
        "recommendation": recommendation,
        "rationale": rationale,
        "current_step": "portfolio_advice_given"
    }



def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate node based on detected intent."""
    intent = state.get("intention", "").upper()
    if intent == "INVESTMENT_ADVICE":
        return "investment_decision"
    elif intent == "MARKET_ANALYSIS":
        return "market_analysis"
    elif intent == "COMPARATIVE_ANALYSIS":
        return "compare_stock"
    elif intent == "PORTFOLIO_ADVICE":
        return "portfolio_advice"
    else:
        return "conversation_end"
    
# --- Graph Construction ---

investment_agent_graph = StateGraph(AgentState)

investment_agent_graph.add_node("identify_intention", identify_intention_node)
investment_agent_graph.add_node("identify_stock", identify_stock_node)
investment_agent_graph.add_node("investment_decision", investment_decision_node)
investment_agent_graph.add_node("compare_stock", compare_stock_node)
investment_agent_graph.add_node("market_analysis", market_analysis_node)
investment_agent_graph.add_node("conversation_end", conversation_end_node)
investment_agent_graph.add_node("portfolio_advice", portfolio_advice_node)
investment_agent_graph.set_entry_point("identify_intention")

investment_agent_graph.add_conditional_edges(
    "identify_intention",
    route_by_intent,
    {
        "investment_decision": "identify_stock",
        "market_analysis": "market_analysis",
        "compare_stock": "identify_stock",
        "conversation_end": "conversation_end",
        "portfolio_advice": "portfolio_advice",

    }
)

#investment_agent_graph.add_edge("identify_intention", "identify_stock")

investment_agent_graph.add_conditional_edges(
    "identify_stock",
    lambda state: state["intention"],
    {
        "INVESTMENT_ADVICE": "investment_decision",
        "COMPARATIVE_ANALYSIS": "compare_stock",
        "MARKET_ANALYSIS": "market_analysis",
        "PORTFOLIO_ADVICE": "portfolio_advice",
        "OTHER": "conversation_end",
    }
)

investment_agent_graph.add_edge("investment_decision", END)
investment_agent_graph.add_edge("compare_stock", END)
investment_agent_graph.add_edge("market_analysis", END)
investment_agent_graph.add_edge("conversation_end", END)

app = investment_agent_graph.compile()
