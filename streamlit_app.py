import streamlit as st
import requests
import json
import uuid
import re
import os
from PIL import Image
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Page Configurations & Styles
st.set_page_config(
    page_title="AI Travel Agentic Planner",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS for Premium Chat Styling
st.markdown("""
<style>
/* Smooth font loading & setting */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom card container styling */
.booking-card {
    background-color: #1E222B;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    border-left: 5px solid #4CAF50;
    box-shadow: 0 4px 6px rgba(0,0,0,0.15);
}

.ticket-card {
    background-color: #1E222B;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    border-left: 5px solid #FF9800;
    box-shadow: 0 4px 6px rgba(0,0,0,0.15);
}

/* Hero Title style */
.hero-title {
    text-align: center;
    font-size: 2.8rem;
    font-weight: 800;
    background: -webkit-linear-gradient(#FF8A8A, #FF4B4B);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 15px;
    margin-bottom: 5px;
}
.hero-subtitle {
    text-align: center;
    font-size: 1.2rem;
    color: #A0A5B5;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

# Helper function to extract Map URL from agent output
def extract_map_url(text: str) -> str:
    # Match standard OpenStreetMap embed links inside the text
    pattern = r'(https://www\.openstreetmap\.org/export/embed\.html\S+)'
    match = re.search(pattern, text)
    if match:
        url = match.group(1)
        # Strip trailing parentheses, quotes, or markdown brackets
        return url.rstrip(')"\' ]')
    return None

# Sidebar Configurations
st.sidebar.title("🗺️ Agent Configuration")

# Check backend status
backend_healthy = False
try:
    health_resp = requests.get("http://localhost:8000/health", timeout=2)
    if health_resp.status_code == 200:
        backend_healthy = True
except Exception:
    pass

if backend_healthy:
    st.sidebar.success("🟢 Connected to FastAPI Backend")
else:
    st.sidebar.error("🔴 Backend Offline (Start FastAPI on port 8000)")

# API Keys Configuration
st.sidebar.markdown("### 🔑 API Keys Setup")
st.sidebar.info("Provide keys below or configure them in a `.env` file in the project folder.")

groq_key_input = st.sidebar.text_input(
    "Groq API Key",
    type="password",
    value=os.environ.get("GROQ_API_KEY", ""),
    placeholder="gsk_..."
)

tavily_key_input = st.sidebar.text_input(
    "Tavily Search API Key",
    type="password",
    value=os.environ.get("TAVILY_API_KEY", ""),
    placeholder="tvly-..."
)

weather_key_input = st.sidebar.text_input(
    "OpenWeather API Key",
    type="password",
    value=os.environ.get("OPENWEATHER_API_KEY", ""),
    placeholder="Enter weather API key..."
)

st.sidebar.markdown("---")
# Travel parameters to inject as default context or clear button
if st.sidebar.button("🗑️ Clear Chat Memory"):
    st.session_state["chat_history"] = []
    st.session_state["thread_id"] = str(uuid.uuid4())
    st.success("Chat history cleared!")

# Display Banner Image
if os.path.exists("banner.png"):
    banner_img = Image.open("banner.png")
    st.image(banner_img, use_column_width=True)

st.markdown('<div class="hero-title">AI Travel Planner Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">FastAPI backend executing LangGraph tool-calling ReAct workflow</div>', unsafe_allow_html=True)

# Session State Setup
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

# Set environment variables dynamically from inputs
if groq_key_input:
    os.environ["GROQ_API_KEY"] = groq_key_input
if tavily_key_input:
    os.environ["TAVILY_API_KEY"] = tavily_key_input
if weather_key_input:
    os.environ["OPENWEATHER_API_KEY"] = weather_key_input

# Display Conversation History
for chat in st.session_state["chat_history"]:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])
        
        # If the history message contains a map, render it
        map_url = extract_map_url(chat["content"])
        if map_url:
            st.markdown("**🗺️ Embedded Map View:**")
            st.iframe(map_url, height=450)

# Input Field
user_query = st.chat_input("Ask the travel agent (e.g. 'Plan a 5-day trip to Goa from Delhi' or 'Search hotels in Tokyo')")

if user_query:
    # Append user message
    st.session_state["chat_history"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
        
    # Query FastAPI Backend
    with st.chat_message("assistant"):
        with st.spinner("Agent calling tools and reasoning..."):
            try:
                payload = {
                    "query": user_query,
                    "thread_id": st.session_state["thread_id"],
                    "groq_api_key": groq_key_input if groq_key_input else None
                }
                
                response = requests.post("http://localhost:8000/query", json=payload, timeout=60)
                
                if response.status_code == 200:
                    answer = response.json()["response"]
                    st.markdown(answer)
                    st.session_state["chat_history"].append({"role": "assistant", "content": answer})
                    
                    # Check and render map if present in response
                    map_url = extract_map_url(answer)
                    if map_url:
                        st.markdown("**🗺️ Embedded Map View:**")
                        st.iframe(map_url, height=450)
                else:
                    err_msg = f"Error from backend: {response.json().get('detail', 'Unknown Error')}"
                    st.error(err_msg)
            except Exception as e:
                st.error(f"Failed to connect to FastAPI backend: {e}")
