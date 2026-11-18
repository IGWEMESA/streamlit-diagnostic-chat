import streamlit as st
import requests
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(dotenv_path="../.env.local")

# --- Configuration ---
# Pull credentials from environment variables
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.syntax-institut.de/webhook/chat-interface")
USERNAME = os.getenv("N8N_USERNAME", "Amaechi")
PASSWORD = os.getenv("N8N_PASSWORD", "Smartoo2105#")

# Create the Basic Auth header
auth_string = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth_string}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="AutoDiag AI Support", page_icon="🤖")
st.title("🤖 AutoDiag AI Support")
st.caption("AI-Powered Diagnostic Assistant · Connected to n8n Agent")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept new user input
if prompt := st.chat_input("Describe the sensor anomaly..."):
    # 1. Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Call n8n Webhook
    with st.chat_message("assistant"):
        with st.spinner("Analyzing anomaly..."):
            try:
                # Prepare payload matching your n8n Webhook expectations
                payload = {
                    "chatInput": prompt,
                    "sessionId": st.session_state.get("session_id", "streamlit-user")
                }
                
                response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=HEADERS)
                response.raise_for_status()
                
                # Extract response (adjust based on your n8n "Respond to Webhook" node)
                data = response.json()
                ai_response = data.get("output", "No response received.")
                
            except Exception as e:
                ai_response = f"Error connecting to the diagnostic agent: {e}"

            # 3. Display and store AI response
            st.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})