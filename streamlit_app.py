import streamlit as st
import requests
import json
import uuid
import re
import os
import pandas as pd
from PIL import Image
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Page Configurations & Styles
st.set_page_config(
    page_title="AI Travel Assistant Dashboard",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS for Premium Chat and Dashboard Styling
st.markdown("""
<style>
/* Smooth font loading & setting */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom travel card container styling */
.travel-card {
    background-color: #1E222B;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 5px solid #FF4B4B;
    box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    transition: transform 0.2s ease-in-out;
}
.travel-card:hover {
    transform: translateY(-1px);
}

/* Day title headers */
.day-title {
    color: #FF4B4B;
    font-weight: 700;
    font-size: 1.4rem;
    margin-top: 15px;
    margin-bottom: 8px;
    border-bottom: 2px solid rgba(255, 75, 75, 0.15);
    padding-bottom: 4px;
}

/* Cost and meal badges */
.badge-meal {
    background-color: rgba(255, 75, 75, 0.12);
    color: #FF7B7B;
    border: 1px solid rgba(255, 75, 75, 0.25);
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.8rem;
    display: inline-block;
    margin-top: 6px;
}
.badge-cost {
    background-color: rgba(76, 175, 80, 0.12);
    color: #81C784;
    border: 1px solid rgba(76, 175, 80, 0.25);
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.8rem;
    display: inline-block;
    font-weight: 600;
}

/* Hero Title style */
.hero-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: 800;
    background: -webkit-linear-gradient(#FF8A8A, #FF4B4B);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 5px;
    margin-bottom: 2px;
}
.hero-subtitle {
    text-align: center;
    font-size: 1.1rem;
    color: #A0A5B5;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# Helper function to extract Map URL from agent output
def extract_map_url(text: str) -> str:
    pattern = r'(https://www\.openstreetmap\.org/export/embed\.html\S+)'
    match = re.search(pattern, text)
    if match:
        url = match.group(1)
        return url.rstrip(')"\' ]')
    return None

# Helper to convert parsed JSON itinerary to markdown format
def itinerary_to_markdown(itinerary: dict) -> str:
    md = []
    md.append(f"# ✈️ AI Trip Itinerary: {itinerary.get('destination', 'Destination')}")
    md.append(f"**Duration**: {itinerary.get('duration_days', 5)} Days\n")
    md.append(f"## 🗺️ Overview\n{itinerary.get('overview', '')}\n")
    md.append(f"- **Best Time to Visit**: {itinerary.get('best_time_to_visit', '')}")
    md.append(f"- **Weather Summary**: {itinerary.get('weather_forecast_summary', '')}\n")
    
    md.append("## 📦 Packing Checklist")
    for item in itinerary.get('packing_checklist', []):
        md.append(f"- [ ] {item}")
    md.append("")
    
    md.append("## 📅 Daily Plans")
    for day in itinerary.get('daily_plans', []):
        md.append(f"\n### Day {day.get('day_number')}: {day.get('theme')}")
        for activity in day.get('activities', []):
            cost = "Free" if activity.get('estimated_cost_usd', 0) == 0 else f"${activity.get('estimated_cost_usd'):.2f}"
            md.append(f"#### 🌅 {activity.get('time_of_day')} - {activity.get('activity_name')} ({cost})")
            md.append(f"{activity.get('description')}")
            if activity.get('suggested_meal'):
                md.append(f"*🍽️ Suggested Meal*: {activity.get('suggested_meal')}")
            md.append("")
            
    md.append("## 💰 Budget Breakdown")
    for cost in itinerary.get('budget_breakdown', []):
        md.append(f"- **{cost.get('category')}**: ${cost.get('estimated_cost_usd', 0):.2f} — *{cost.get('notes')}*")
    md.append("")
    
    md.append("## 💡 General Travel Tips")
    for tip in itinerary.get('general_travel_tips', []):
        md.append(f"### {tip.get('title')}\n{tip.get('details')}\n")
        
    return "\n".join(md)

# Sidebar Configurations
st.sidebar.title("🗺️ Configuration")

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
st.sidebar.info("Configure keys below or setup a local `.env` file.")

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
if st.sidebar.button("🗑️ Clear Chat Memory"):
    st.session_state["chat_history"] = []
    st.session_state["thread_id"] = str(uuid.uuid4())
    st.session_state["itinerary_data"] = None
    st.success("Chat and dashboard cleared!")

# Display Banner Image
if os.path.exists("banner.png"):
    banner_img = Image.open("banner.png")
    st.image(banner_img, width=1100)

st.markdown('<div class="hero-title">AI Travel Assistant Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Unified AI agent conversation panel and interactive multi-tab travel itinerary dashboard</div>', unsafe_allow_html=True)

# Session State Setup
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())
if "itinerary_data" not in st.session_state:
    st.session_state["itinerary_data"] = None

# Update environment dynamically
if groq_key_input:
    os.environ["GROQ_API_KEY"] = groq_key_input
if tavily_key_input:
    os.environ["TAVILY_API_KEY"] = tavily_key_input
if weather_key_input:
    os.environ["OPENWEATHER_API_KEY"] = weather_key_input

# ---------------------------------------------------------
# Dual-Column Main Layout
# ---------------------------------------------------------
col_chat, col_dashboard = st.columns([1.1, 0.9])

# --- Column 1: Chat Assistant panel ---
with col_chat:
    st.markdown("### 💬 Chat with AI Travel Planner")
    
    # Scrollable container for chat history
    chat_container = st.container(height=500)
    with chat_container:
        if len(st.session_state["chat_history"]) == 0:
            st.write("👋 *Hello! I am your AI travel agent. Tell me where you want to go, starting location, travel dates, or ask me to search hotels and book flight tickets!*")
        
        for chat in st.session_state["chat_history"]:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])
                
                # Check for OpenStreetMap URL inside chat
                map_url = extract_map_url(chat["content"])
                if map_url:
                    st.iframe(map_url, height=350)
                    
    # Chat inputs
    user_query = st.chat_input("Ask the agent: 'Plan a 5-day trip to Goa from Delhi' or 'Search tickets to Paris'...")
    
    if user_query:
        # Append User input
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        
        # Display immediately in chat
        chat_container.chat_message("user").write(user_query)
        
        # Send API Request
        with chat_container.chat_message("assistant"):
            with st.spinner("Thinking and invoking tools..."):
                try:
                    payload = {
                        "query": user_query,
                        "thread_id": st.session_state["thread_id"],
                        "groq_api_key": groq_key_input if groq_key_input else None
                    }
                    response = requests.post("http://localhost:8000/query", json=payload, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data["response"]
                        st.markdown(answer)
                        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
                        
                        # Render Map if returned
                        map_url = extract_map_url(answer)
                        if map_url:
                            st.iframe(map_url, height=350)
                            
                        # If the agent updated the itinerary dashboard data, update it in session state
                        if data.get("itinerary_data"):
                            st.session_state["itinerary_data"] = data["itinerary_data"]
                            # Trigger a rerun to refresh the dashboard panel
                            st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Failed to connect to FastAPI: {e}")

# --- Column 2: Visual Trip Dashboard panel ---
with col_dashboard:
    st.markdown("### 📋 Interactive Trip Dashboard")
    
    if st.session_state["itinerary_data"]:
        try:
            itinerary = json.loads(st.session_state["itinerary_data"])
            
            # Destination and days header
            st.markdown(f"#### 🌍 Plan: {itinerary.get('destination')} ({itinerary.get('duration_days')} Days)")
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🗺️ Overview", 
                "📅 Day-by-Day", 
                "💰 Expenses", 
                "💡 Travel Tips", 
                "📥 Export"
            ])
            
            # Tab 1: Overview
            with tab1:
                st.markdown(f"**Overview:** {itinerary.get('overview')}")
                st.info(f"📅 **Best Season to Visit:**\n\n{itinerary.get('best_time_to_visit')}")
                st.success(f"☀️ **Weather Forecast:**\n\n{itinerary.get('weather_forecast_summary')}")
                
                st.markdown("##### 📦 Travel Packing Checklist")
                for idx, item in enumerate(itinerary.get('packing_checklist', [])):
                    st.checkbox(item, key=f"pack_check_{idx}")
                    
            # Tab 2: Day-by-Day Itinerary
            with tab2:
                for day in itinerary.get('daily_plans', []):
                    st.markdown(f'<div class="day-title">Day {day.get("day_number")}: {day.get("theme")}</div>', unsafe_allow_html=True)
                    
                    for activity in day.get('activities', []):
                        cost_val = activity.get('estimated_cost_usd', 0)
                        cost_txt = "Free" if cost_val == 0 else f"${cost_val:.2f}"
                        meal_txt = f'<div class="badge-meal">🍽️ Recommended Meal: {activity.get("suggested_meal")}</div>' if activity.get('suggested_meal') else ''
                        
                        st.markdown(f"""
                        <div class="travel-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <h5 style="margin: 0; color: #FAFAFA;">🌅 {activity.get('time_of_day')} • {activity.get('activity_name')}</h5>
                                <span class="badge-cost">💰 {cost_txt}</span>
                            </div>
                            <p style="margin: 0 0 6px 0; font-size: 0.9rem; color: #D1D5DB; line-height: 1.4;">{activity.get('description')}</p>
                            {meal_txt}
                        </div>
                        """, unsafe_allow_html=True)
                        
            # Tab 3: Budget Breakdown
            with tab3:
                st.markdown("##### Estimated Expenses breakdown")
                
                costs_list = []
                for cost in itinerary.get('budget_breakdown', []):
                    costs_list.append({
                        "Category": cost.get("category"),
                        "Cost (USD)": cost.get("estimated_cost_usd", 0),
                        "Description Notes": cost.get("notes")
                    })
                    
                df = pd.DataFrame(costs_list)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.markdown("##### Expenses Chart (USD)")
                try:
                    st.bar_chart(df.set_index("Category")["Cost (USD)"])
                except Exception:
                    pass
                    
            # Tab 4: Travel Tips
            with tab4:
                st.markdown("##### Practical Local Guides")
                for tip in itinerary.get('general_travel_tips', []):
                    with st.expander(f"💡 {tip.get('title')}", expanded=True):
                        st.write(tip.get('details'))
                        
            # Tab 5: Export options
            with tab5:
                st.markdown("##### Export Travel Plan")
                markdown_doc = itinerary_to_markdown(itinerary)
                
                st.download_button(
                    label="📥 Download Itinerary as Markdown (.md)",
                    data=markdown_doc,
                    file_name=f"{itinerary.get('destination').lower().replace(' ', '_')}_itinerary.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                
                st.download_button(
                    label="📥 Download Itinerary as JSON (.json)",
                    data=json.dumps(itinerary, indent=2),
                    file_name=f"{itinerary.get('destination').lower().replace(' ', '_')}_itinerary.json",
                    mime="application/json",
                    use_container_width=True
                )
                
        except Exception as e:
            st.error(f"Error parsing itinerary data: {e}")
            
    else:
        st.markdown("""
        <div style="background-color: #1E222B; border-radius: 12px; padding: 25px; text-align: center; border: 1px solid rgba(255, 75, 75, 0.15); box-shadow: 0 4px 6px rgba(0,0,0,0.15); margin-top: 15px;">
            <h4 style="color: #FF4B4B; margin-top: 0;">Interactive Trip Plan</h4>
            <p style="color: #D1D5DB; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0;">
                Once you instruct the AI chatbot on the left to plan a trip, a structured visual itinerary detailing your overview, day schedules, budget charts, local tips, and markdown downloads will automatically populate here in real-time!
            </p>
        </div>
        """, unsafe_allow_html=True)
