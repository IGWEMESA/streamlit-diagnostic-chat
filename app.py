import base64
import html
import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env.local (local development)
load_dotenv(dotenv_path="../.env.local")


def get_setting(name: str, default: str = "") -> str:
    """Read a setting from env vars first, then from Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


# --- Configuration ---
N8N_WEBHOOK_URL = get_setting(
    "N8N_WEBHOOK_URL", "https://n8n.syntax-institut.de/webhook/chat-interface"
)

USERNAME = get_setting("N8N_USERNAME")
PASSWORD = get_setting("N8N_PASSWORD")

REQUEST_TIMEOUT = 120  # seconds

# --- Page setup ---
st.set_page_config(page_title="AutoDiag AI Support", page_icon="🤖", layout="centered")

if not USERNAME or not PASSWORD:
    st.error("Configuration missing: please set N8N_USERNAME and N8N_PASSWORD.")
    st.stop()

# Create the Basic Auth header
auth_string = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth_string}",
    "Content-Type": "application/json",
}

# --- Custom CSS ---
st.markdown(
    """
    <style>
    /* Main background */
    .stApp {
        background-color: #09090b;
        color: #e4e4e7;
        font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    }
    /* Title styling */
    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    /* User Message Bubble */
    .user-message {
        background-color: #10b981; /* Emerald green */
        color: #ffffff;
        padding: 16px;
        border-radius: 12px 12px 0 12px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        font-size: 14px;
    }
    /* AI Message Bubble */
    .ai-message {
        background-color: #18181b; /* Dark gray */
        color: #e4e4e7;
        padding: 20px;
        border-radius: 12px 12px 12px 0;
        margin-bottom: 16px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        font-size: 14px;
        line-height: 1.6;
    }
    /* Chat input box styling */
    .stTextInput > div > div > input {
        background-color: #18181b !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
    }
    /* Hide the default Streamlit chat styling to use our custom HTML */
    [data-testid="stChatMessage"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 AutoDiag AI Support")
st.caption("AI-Powered Diagnostic Assistant · Connected to n8n Agent")

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# One session ID per visitor (used by n8n for chat memory)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# --- Helpers ---
def render_message(role: str, content: str) -> None:
    """Render a chat bubble. Text is HTML-escaped; line breaks are preserved."""
    css_class = "user-message" if role == "user" else "ai-message"
    safe_text = html.escape(content).replace("\n", "<br>")
    st.markdown(f'<div class="{css_class}">{safe_text}</div>', unsafe_allow_html=True)


def ask_agent(prompt: str) -> str:
    """Send the message to the n8n webhook and return a user-friendly answer."""
    fallback = (
        "I couldn't process this request. Please send a sensor reading "
        "(sensor name, magnitude, status) or ask a question about the diagnostic system."
    )
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json={"chatInput": prompt, "sessionId": st.session_state.session_id},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        # n8n returned nothing (e.g. a branch without a response node)
        if not response.text.strip():
            return fallback

        data = response.json()
        output = data.get("output") if isinstance(data, dict) else None
        return str(output).strip() if output else fallback

    except requests.exceptions.Timeout:
        return "The diagnostic agent took too long to respond. Please try again."
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 401:
            return "Authentication with the diagnostic service failed. Please contact support."
        return f"The diagnostic service returned an error ({status}). Please try again later."
    except ValueError:
        return "The diagnostic agent returned an unexpected response. Please try again."
    except requests.exceptions.RequestException:
        return "Could not reach the diagnostic agent. Please check your connection and try again."


# --- Display existing chat messages ---
for message in st.session_state.messages:
    render_message(message["role"], message["content"])

# --- Accept new user input ---
if prompt := st.chat_input("Describe the sensor anomaly..."):
    # 1. Display and store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_message("user", prompt)

    # 2. Call n8n webhook
    with st.spinner("Analyzing anomaly..."):
        ai_response = ask_agent(prompt)

    # 3. Display and store AI response
    render_message("assistant", ai_response)
    st.session_state.messages.append({"role": "assistant", "content": ai_response})