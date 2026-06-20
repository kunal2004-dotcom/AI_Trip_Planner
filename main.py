import streamlit as st
import pandas as pd
from PIL import Image
import json
import os
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Configurations & Styles
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Trip Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Styling
st.markdown("""
<style>
/* Smooth font loading & setting */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom card container styling */
.travel-card {
    background-color: #1E222B;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 5px solid #FF4B4B;
    box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    transition: transform 0.2s ease-in-out;
}
.travel-card:hover {
    transform: translateY(-2px);
}

/* Day title headers */
.day-title {
    color: #FF4B4B;
    font-weight: 700;
    font-size: 1.6rem;
    margin-top: 20px;
    margin-bottom: 10px;
    border-bottom: 2px solid rgba(255, 75, 75, 0.2);
    padding-bottom: 5px;
}

/* Cost and meal badges */
.badge-meal {
    background-color: rgba(255, 75, 75, 0.12);
    color: #FF7B7B;
    border: 1px solid rgba(255, 75, 75, 0.25);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.85rem;
    display: inline-block;
    margin-top: 8px;
}
.badge-cost {
    background-color: rgba(76, 175, 80, 0.12);
    color: #81C784;
    border: 1px solid rgba(76, 175, 80, 0.25);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.85rem;
    display: inline-block;
    font-weight: 600;
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

# ---------------------------------------------------------
# Pydantic Schemas for Structured Gemini Outputs
# ---------------------------------------------------------
class Activity(BaseModel):
    time_of_day: str = Field(description="Morning, Afternoon, or Evening")
    activity_name: str = Field(description="Name of the activity or place to visit")
    description: str = Field(description="Detailed description of what to see/do, transit tips, or recommendations")
    suggested_meal: Optional[str] = Field(None, description="Suggested restaurant, cafe, or local dish to try during/after this activity")
    estimated_cost_usd: float = Field(description="Estimated cost in USD (0 if free)")

class DayPlan(BaseModel):
    day_number: int
    theme: str = Field(description="The theme or main focus of the day (e.g., 'Historical Wonders', 'Local Cuisine Exploration')")
    activities: List[Activity]

class CostCategory(BaseModel):
    category: str = Field(description="Category (e.g., Accommodation, Food, Activities, Transport, Miscellaneous)")
    estimated_cost_usd: float
    notes: str = Field(description="Reasoning/details for this estimate")

class TravelTip(BaseModel):
    title: str
    details: str

class TripItinerary(BaseModel):
    destination: str
    duration_days: int
    overview: str = Field(description="An overall summary of the trip, general vibe, and what to expect")
    best_time_to_visit: str = Field(description="Best months or season to visit and why")
    weather_forecast_summary: str = Field(description="General expected weather pattern for this duration")
    packing_checklist: List[str] = Field(description="Recommended items to pack tailored to this destination and season")
    daily_plans: List[DayPlan]
    budget_breakdown: List[CostCategory]
    general_travel_tips: List[TravelTip]

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)

def generate_itinerary(client: genai.Client, destination: str, duration: int, travel_group: str, budget: str, interests: List[str], preferences: str) -> TripItinerary:
    interests_str = ", ".join(interests) if interests else "General sightseeing"
    prompt = f"""
    Generate a detailed, premium trip itinerary for a {duration}-day trip to {destination}.
    
    Travel Details:
    - Travel Group: {travel_group}
    - Budget Tier: {budget}
    - Main Interests: {interests_str}
    - Additional Preferences/Restrictions: {preferences if preferences else 'None'}
    
    Ensure the recommendations are highly tailored, realistic, and organized. Provide practical estimates for costs.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TripItinerary,
            temperature=0.2,
        ),
    )
    return TripItinerary.model_validate_json(response.text)

def modify_itinerary(client: genai.Client, current_itinerary: TripItinerary, modification_request: str) -> TripItinerary:
    prompt = f"""
    You are an expert travel assistant. You are given a current trip itinerary (in JSON) and a user's request to modify it.
    Please modify the itinerary according to the user's instructions and return the updated itinerary matching the exact same schema.
    
    Current Itinerary:
    {current_itinerary.model_dump_json()}
    
    User's Modification Request:
    "{modification_request}"
    
    Incorporate this change seamlessly. Keep all other parts of the itinerary consistent unless they conflict with the request.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TripItinerary,
            temperature=0.2,
        ),
    )
    return TripItinerary.model_validate_json(response.text)

def itinerary_to_markdown(itinerary: TripItinerary) -> str:
    md = []
    md.append(f"# ✈️ AI Trip Itinerary: {itinerary.destination}")
    md.append(f"**Duration**: {itinerary.duration_days} Days\n")
    md.append(f"## 🗺️ Overview\n{itinerary.overview}\n")
    md.append(f"- **Best Time to Visit**: {itinerary.best_time_to_visit}")
    md.append(f"- **Weather Summary**: {itinerary.weather_forecast_summary}\n")
    
    md.append("## 📦 Packing Checklist")
    for item in itinerary.packing_checklist:
        md.append(f"- [ ] {item}")
    md.append("")
    
    md.append("## 📅 Daily Plans")
    for day in itinerary.daily_plans:
        md.append(f"\n### Day {day.day_number}: {day.theme}")
        for activity in day.activities:
            cost = "Free" if activity.estimated_cost_usd == 0 else f"${activity.estimated_cost_usd:.2f}"
            md.append(f"#### 🌅 {activity.time_of_day} - {activity.activity_name} ({cost})")
            md.append(f"{activity.description}")
            if activity.suggested_meal:
                md.append(f"*🍽️ Suggested Meal*: {activity.suggested_meal}")
            md.append("")
            
    md.append("## 💰 Budget Breakdown")
    for cost in itinerary.budget_breakdown:
        md.append(f"- **{cost.category}**: ${cost.estimated_cost_usd:.2f} — *{cost.notes}*")
    md.append("")
    
    md.append("## 💡 General Travel Tips")
    for tip in itinerary.general_travel_tips:
        md.append(f"### {tip.title}\n{tip.details}\n")
        
    return "\n".join(md)

# ---------------------------------------------------------
# Sidebar Setup & Inputs
# ---------------------------------------------------------
st.sidebar.title("✈️ Trip Configurator")

# API Key Validation
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password", help="Get a key from Google AI Studio")
    if not api_key:
        st.sidebar.warning("🔑 Please enter a Gemini API Key to run the app.")

destination = st.sidebar.text_input("Destination", placeholder="e.g. Kyoto, Japan or Rome, Italy")
duration = st.sidebar.slider("Trip Duration (Days)", min_value=1, max_value=14, value=3)

travel_group = st.sidebar.selectbox(
    "Travel Group",
    ["Solo Traveller", "Couple", "Family with Kids", "Group of Friends"]
)

budget = st.sidebar.selectbox(
    "Budget Tier",
    ["Economy (Budget-friendly)", "Moderate (Value-focused)", "Luxury (High-end)"]
)

interests = st.sidebar.multiselect(
    "Interests & Style",
    ["Culture & History", "Nature & Adventure", "Food & Gastronomy", "Relaxation & Spa", "Shopping & Nightlife", "Family-Friendly"],
    default=["Culture & History", "Food & Gastronomy"]
)

preferences = st.sidebar.text_area(
    "Additional Preferences (Optional)",
    placeholder="e.g. Vegetarian diet, walking-friendly, start days after 10 AM, avoid crowds..."
)

generate_btn = st.sidebar.button("✨ Generate Custom Itinerary", type="primary", disabled=not api_key)

# ---------------------------------------------------------
# Main App Layout
# ---------------------------------------------------------
# Banner Image
if os.path.exists("banner.png"):
    banner_img = Image.open("banner.png")
    st.image(banner_img, use_column_width=True)

st.markdown('<div class="hero-title">AI Trip Planner</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Your personalized, AI-generated travel itineraries in seconds</div>', unsafe_allow_html=True)

# Session State Initialization
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Action: Generate Itinerary
if generate_btn:
    if not destination.strip():
        st.error("Please enter a valid destination!")
    else:
        with st.spinner(f"Planning your dream trip to {destination}... Please wait."):
            try:
                client = get_client(api_key)
                itinerary = generate_itinerary(
                    client=client,
                    destination=destination,
                    duration=duration,
                    travel_group=travel_group,
                    budget=budget,
                    interests=interests,
                    preferences=preferences
                )
                st.session_state["itinerary"] = itinerary
                st.session_state["messages"] = []  # Clear previous revisions chat
                st.success("🎉 Trip itinerary generated successfully!")
            except Exception as e:
                st.error(f"Failed to generate itinerary: {e}")

# Display Itinerary
if st.session_state["itinerary"]:
    itinerary = st.session_state["itinerary"]
    
    st.markdown(f"## 🗺️ Trip to {itinerary.destination} ({itinerary.duration_days} Days)")
    
    # Navigation Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Overview", 
        "📅 Day-by-Day", 
        "💰 Budget Breakdown", 
        "💡 Travel Tips", 
        "📥 Export & Save"
    ])
    
    # Tab 1: Overview
    with tab1:
        st.markdown(f"### Welcome to {itinerary.destination}")
        st.markdown(f"**Overview:** {itinerary.overview}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📅 **Best Time to Visit:**\n\n{itinerary.best_time_to_visit}")
        with col2:
            st.success(f"☀️ **Weather Summary:**\n\n{itinerary.weather_forecast_summary}")
            
        st.markdown("### 📦 Recommended Packing Checklist")
        st.write("Check off items as you pack them:")
        for idx, item in enumerate(itinerary.packing_checklist):
            st.checkbox(item, key=f"packing_{idx}")
            
    # Tab 2: Day-by-Day
    with tab2:
        for day in itinerary.daily_plans:
            st.markdown(f'<div class="day-title">Day {day.day_number}: {day.theme}</div>', unsafe_allow_html=True)
            
            for activity in day.activities:
                cost_text = "Free" if activity.estimated_cost_usd == 0 else f"${activity.estimated_cost_usd:.2f}"
                meal_html = f'<div class="badge-meal">🍽️ Recommended Meal: {activity.suggested_meal}</div>' if activity.suggested_meal else ''
                
                st.markdown(f"""
                <div class="travel-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #FAFAFA; font-size: 1.15rem;">🌅 {activity.time_of_day} • {activity.activity_name}</h4>
                        <span class="badge-cost">💰 {cost_text}</span>
                    </div>
                    <p style="margin: 0 0 8px 0; font-size: 0.95rem; color: #D1D5DB; line-height: 1.5;">{activity.description}</p>
                    {meal_html}
                </div>
                """, unsafe_allow_html=True)
                
    # Tab 3: Budget Breakdown
    with tab3:
        st.markdown("### Estimated Expenses Breakdown")
        
        budget_data = []
        for b in itinerary.budget_breakdown:
            budget_data.append({
                "Category": b.category,
                "Estimated Cost (USD)": b.estimated_cost_usd,
                "Description / Notes": b.notes
            })
            
        df = pd.DataFrame(budget_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Simple Chart
        st.markdown("#### Budget Allocation Visual")
        try:
            st.bar_chart(df.set_index("Category")["Estimated Cost (USD)"])
        except Exception:
            pass
            
    # Tab 4: Travel Tips
    with tab4:
        st.markdown("### Practical Local Tips")
        for tip in itinerary.general_travel_tips:
            with st.expander(f"💡 {tip.title}", expanded=True):
                st.write(tip.details)
                
    # Tab 5: Export & Save
    with tab5:
        st.markdown("### Export your Custom Trip Plan")
        st.markdown("Download your travel plan to keep it handy during your trip.")
        
        markdown_content = itinerary_to_markdown(itinerary)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download as Markdown (.md)",
                data=markdown_content,
                file_name=f"{itinerary.destination.lower().replace(' ', '_')}_itinerary.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📥 Download as JSON (.json)",
                data=itinerary.model_dump_json(indent=2),
                file_name=f"{itinerary.destination.lower().replace(' ', '_')}_itinerary.json",
                mime="application/json",
                use_container_width=True
            )
            
    # ---------------------------------------------------------
    # Chat Revision/Adjustment Section
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### 💬 Customize & Refine Your Trip")
    st.write("Want to tweak something? Ask the AI Travel Assistant to update the itinerary (e.g. *'Make day 2 food options vegan'*, or *'Add a museum visit on day 1 morning'*).")
    
    # Prompt for adjustments
    revision_query = st.text_input("Enter modification request:", placeholder="e.g. Add more beach time to Day 3, or replace high-cost activities with free alternatives")
    submit_revision = st.button("Apply Adjustments")
    
    if submit_revision and revision_query.strip():
        with st.spinner("Revising itinerary details... Please wait."):
            try:
                client = get_client(api_key)
                updated_itinerary = modify_itinerary(
                    client=client,
                    current_itinerary=itinerary,
                    modification_request=revision_query
                )
                st.session_state["itinerary"] = updated_itinerary
                st.success("🔄 Itinerary updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to modify itinerary: {e}")

else:
    # Welcome Card when no trip is loaded
    st.markdown("""
    <div style="background-color: #1E222B; border-radius: 12px; padding: 30px; text-align: center; border: 1px solid rgba(255, 75, 75, 0.2); box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
        <h3 style="color: #FF4B4B; margin-top: 0;">Plan Your Next Adventure</h3>
        <p style="color: #D1D5DB; font-size: 1.1rem; max-width: 600px; margin: 0 auto 20px auto;">
            Configure your destination, budget, group size, and interests in the sidebar panel, and hit <b>Generate Custom Itinerary</b> to create a beautifully detailed day-by-day plan tailored specifically for you.
        </p>
        <span style="font-size: 2.5rem;">🌍✈️🧳🗺️</span>
    </div>
    """, unsafe_allow_html=True)
