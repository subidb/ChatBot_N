from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import re
import json
import os
from dateparser import parse
from langchain.chat_models import ChatOpenAI
from config import OPENAI_API_KEY
from spellchecker import SpellChecker

# Initialize Router
router = APIRouter()

# Initialize LLM and Spell Checker
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)
spell = SpellChecker()

# -------------------------------
# 📅 Appointment Booking
# -------------------------------
APPOINTMENTS_FILE = "appointments.json"

# Load existing appointments from file
if os.path.exists(APPOINTMENTS_FILE):
    with open(APPOINTMENTS_FILE, "r") as f:
        appointments = json.load(f)
else:
    appointments = []


class Appointment(BaseModel):
    name: str
    email: EmailStr
    phone: str
    date: str  # YYYY-MM-DD format


@router.post("/book_appointment/")
async def book_appointment(name: str, email: EmailStr, phone: str, date: str):
    # Validate phone number
    if not re.match(r"^\+?\d{10,15}$", phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format.")
    
    # Validate date format
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Save appointment
    appointment = {
        "name": name,
        "email": email,
        "phone": phone,
        "date": parsed_date.isoformat()
    }
    appointments.append(appointment)
    
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f, indent=4)
    
    return {"message": "Appointment booked successfully", "appointment": appointment}


@router.get("/appointments/")
async def get_appointments():
    return {"appointments": appointments}


# -------------------------------
# 📆 Parse Natural Language Date
# -------------------------------
@router.get("/parse_date/")
async def parse_date(query: str):
    try:
        # Step 1: Spellcheck and correct obvious typos
        corrected_words = [spell.correction(word) or word for word in query.split()]
        corrected_query = ' '.join(corrected_words)
        
        # Step 2: Explicitly handle relative terms locally
        today = datetime.now()
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        
        if "next" in corrected_query.lower() and any(day in corrected_query.lower() for day in weekdays):
            day_name = corrected_query.split(" ")[1].lower()
            days_ahead = (weekdays[day_name] - today.weekday() + 7) % 7
            days_ahead = days_ahead or 7  # Ensure it's always the following week
            parsed_date = today + timedelta(days=days_ahead)
            return {"parsed_date": parsed_date.strftime("%Y-%m-%d")}
        
        # Step 3: Attempt date parsing locally with dateparser
        parsed_date = parse(corrected_query, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': today})
        if parsed_date:
            return {"parsed_date": parsed_date.strftime("%Y-%m-%d")}
        
        # Step 4: Fallback to OpenAI
        prompt = (
            f"Today's date is {today.strftime('%Y-%m-%d')}. Extract and return the date from the following query in ISO 8601 format (YYYY-MM-DD). "
            "Correct any spelling mistakes if present. If no valid date is found, respond with 'None'. "
            "Only return the date, nothing else.\n"
            f"Query: {corrected_query}"
        )
        
        response = llm.predict(prompt).strip()
        
        # Validate the response
        if not re.match(r"\d{4}-\d{2}-\d{2}", response):
            raise HTTPException(status_code=400, detail="Unable to parse date from query.")
        
        return {"parsed_date": response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
