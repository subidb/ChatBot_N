from fastapi import FastAPI, Query
from langchain.chat_models import ChatOpenAI
from config import OPENAI_API_KEY
from services import router as services_router
from document_ingest import query_document  # Avoid dynamic imports
import re

# Initialize FastAPI
app = FastAPI()

# Add service routes from services.py
app.include_router(services_router)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)


def detect_intent(query: str) -> str:
    """
    Detect intent from user query.
    Returns one of: document_query, appointment_booking, general_chat
    """
    prompt = (
        "Classify the following query into one of these intents:\n"
        "1. document_query (if the query is about nexGenTech, finances, companies, company plans, personnel changes, revenue, document content, or data)\n"
        "2. appointment_booking (if the query is about scheduling or calling booking an appointment)\n"
        "3. general_chat (if the query is casual conversation or doesn't fit the above)\n\n"
        f"Query: {query}\n"
        "Intent:"
    )

    print(f"📝 **Prompt Sent to LLM:**\n{prompt}")
    try:
        response = llm.invoke(prompt).content.strip().lower()
        print(f"🧠 **LLM Raw Response:** {response}")
        if "document_query" in response:
            return "document_query"
        if "appointment_booking" in response:
            return "appointment_booking"
        if "general_chat" in response:
            return "general_chat"
        return "general_chat"
    except Exception as e:
        print(f"❌ **Error during intent detection:** {e}")
        return "general_chat"


@app.get("/chat/")
async def chat(query: str = Query(..., description="User query to the chatbot")):
    intent = detect_intent(query)
    print(f"🔍 **Detected Intent:** {intent}")
    
    if intent == "document_query":
        response = query_document(query)
        return {"intent": "document_query", "response": response}
    
    if intent == "appointment_booking":
        return {
            "intent": "appointment_booking",
            "response": "Let's start by selecting a date for your appointment. Please provide your preferred date."
        }
    
    if intent == "general_chat":
        prompt = f"You are a helpful assistant. Answer the following question concisely:\n{query}"
        try:
            general_response = llm.invoke(prompt).content.strip()
            return {"intent": "general_chat", "response": general_response}
        except Exception as e:
            return {"intent": "general_chat", "response": str(e)}
