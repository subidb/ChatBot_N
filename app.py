import streamlit as st
import requests

# Streamlit Chatbot UI
st.title("🤖 Chatbot Interface")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_input" not in st.session_state:
    st.session_state.last_input = ""
if "input_key" not in st.session_state:
    st.session_state.input_key = 0  # Key for resetting the input box
if "appointment_stage" not in st.session_state:
    st.session_state.appointment_stage = None
if "appointment_date" not in st.session_state:
    st.session_state.appointment_date = None
if "appointment_details" not in st.session_state:
    st.session_state.appointment_details = {}

# Display chat history
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.text_area("You", value=message["content"], height=70, disabled=True, key=f"user_{idx}")
    else:
        st.text_area("Bot", value=message["content"], height=150, disabled=True, key=f"bot_{idx}")

# Reset Chat Button
if st.button("🔄 Reset Chat"):
    st.session_state.messages = []
    st.session_state.last_input = ""
    st.session_state.appointment_stage = None
    st.session_state.appointment_date = None
    st.session_state.appointment_details = {}
    st.session_state.input_key = 0
    st.rerun()

# Handle Appointment Booking Stages
if st.session_state.appointment_stage == "date":
    user_input = st.text_input("📅 Enter your preferred appointment date:", key="date_input")
    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input  # Prevent duplicate triggers

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        try:
            response = requests.get("http://127.0.0.1:8000/parse_date/", params={"query": user_input})
            if response.status_code == 200:
                parsed_date = response.json().get("parsed_date", None)
                if parsed_date:
                    st.session_state.appointment_date = parsed_date
                    st.session_state.appointment_stage = "form"
                    st.session_state.messages.append({"role": "bot", "content": f"📅 Date confirmed: {parsed_date}. Now, please fill out your details below."})
                    st.rerun()
                else:
                    st.session_state.messages.append({"role": "bot", "content": "❌ I couldn't parse the date. Please try again with a clearer format."})
            else:
                st.session_state.messages.append({"role": "bot", "content": "❌ Error processing the date. Please try again."})
        except Exception as e:
            st.session_state.messages.append({"role": "bot", "content": f"❌ Error: {e}"})
        st.rerun()

# Show Appointment Form
if st.session_state.appointment_stage == "form":
    with st.form(key='appointment_form'):
        name = st.text_input("👤 Name")
        email = st.text_input("📧 Email")
        phone = st.text_input("📱 Phone")
        submit_button = st.form_submit_button("✅ Confirm Appointment")
    
    if submit_button:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/book_appointment/",
                params={
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "date": st.session_state.appointment_date
                }
            )
            if response.status_code == 200:
                st.session_state.appointment_details = {
                    "date": st.session_state.appointment_date,
                    "name": name,
                    "email": email,
                    "phone": phone
                }
                confirmation_message = (
                    "✅ **Appointment Successfully Booked!**\n\n"
                    f"Date: {st.session_state.appointment_details['date']}\n"
                    f"Name: {st.session_state.appointment_details['name']}\n"
                    f"Email: {st.session_state.appointment_details['email']}\n"
                    f"Phone: {st.session_state.appointment_details['phone']}"
                )
                st.session_state.messages.append({"role": "bot", "content": confirmation_message})
                st.session_state.appointment_stage = None
                st.session_state.appointment_date = None
                st.session_state.appointment_details = {}
                st.rerun()
            else:
                st.session_state.messages.append({"role": "bot", "content": "❌ Failed to book the appointment. Please try again with correct details."})
        except Exception as e:
            st.session_state.messages.append({"role": "bot", "content": f"❌ Error: {e}"})
        st.rerun()

# Process General Chat
user_input = st.text_input(
    "💬 Type your message here:",
    key=f"user_input_{st.session_state.input_key}",
    placeholder="Type your message..."
)

if user_input and user_input != st.session_state.last_input and not st.session_state.appointment_stage:
    st.session_state.last_input = user_input  # Prevent duplicate triggers

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        # Send user query to FastAPI backend
        response = requests.get("http://127.0.0.1:8000/chat/", params={"query": user_input})
        if response.status_code == 200:
            st.write("🔍 Backend Response:", response.json())  # Debugging Response
            intent = response.json().get("intent", "unknown")
            bot_response = response.json().get("response", "Sorry, I didn't understand that.")

            # Handle appointment intent
            if intent == "appointment_booking":
                st.session_state.appointment_stage = "date"
                bot_response = "📅 Sure! What date would you like to book the appointment for?"

            # Handle document query intent
            elif intent == "document_query":
                bot_response = response.json().get("response", "I couldn't find the document data you're asking about.")
            
            # Handle general chat
            elif intent == "general_chat":
                bot_response = response.json().get("response", "I'm here to help with your questions!")
        else:
            bot_response = f"❌ Error: {response.status_code}"
    except Exception as e:
        bot_response = f"❌ Error: {e}"
    
    # Add bot response to chat history
    st.session_state.messages.append({"role": "bot", "content": bot_response})
    st.session_state.input_key += 1  
    st.rerun()
