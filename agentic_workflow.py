import os
from typing import TypedDict, Annotated, Sequence, Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import json

# Load local environment variables
load_dotenv()

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# ---------------------------------------------------------
# Pydantic Schemas for Itinerary Structure
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
# Tool Definitions (Mapping to Core Tool Python files)
# ---------------------------------------------------------
@tool
def get_weather_tool(city: str) -> str:
    """
    Get the current weather and 3-day weather forecast for a given city/destination.
    Useful for planning packing checklists and activities.
    """
    from tools.weather import get_weather
    return get_weather(city)

@tool
def search_places_tool(query: str) -> str:
    """
    Search for tourist attractions, places to visit, restaurants, or hotels.
    Use this to find specific landmarks and recommendations for a destination.
    """
    from tools.search import search_places
    return search_places(query)

@tool
def convert_currency_tool(amount: float, from_curr: str = "USD", to_curr: str = "INR") -> str:
    """
    Convert a specific amount from one currency to another (e.g. from USD to INR, or EUR to INR).
    Useful for currency planning and budget estimation.
    """
    from tools.currency import convert_currency
    return convert_currency(amount, from_curr, to_curr)

@tool
def calculate_expenses_tool(destination: str, days: int, budget_tier: str, travel_group: str) -> str:
    """
    Calculate and estimate total travel expenses based on destination, days, budget tier, and travel group.
    Returns a categorized cost breakdown in USD and INR.
    """
    from tools.expense import calculate_expenses
    return calculate_expenses(destination, days, budget_tier, travel_group)

@tool
def search_tickets_tool(from_location: str, to_location: str, travel_date: str, vehicle_type: str = "Flight") -> str:
    """
    Search for travel tickets (Flight, Train, or Bus) from a starting location to a destination on a given date.
    Returns list of options, departure times, and prices.
    """
    from tools.booking import search_tickets
    return search_tickets(from_location, to_location, travel_date, vehicle_type)

@tool
def book_ticket_tool(from_location: str, to_location: str, travel_date: str, carrier: str, price_inr: float, passenger_name: str) -> str:
    """
    Book a travel ticket for a passenger on a specific carrier from starting location to destination.
    Returns confirmation details including Ticket PNR and seat number.
    """
    from tools.booking import book_ticket
    return book_ticket(from_location, to_location, travel_date, carrier, price_inr, passenger_name)

@tool
def search_hotels_tool(destination: str, checkin_date: str, checkout_date: str, hotel_tier: str = "Moderate") -> str:
    """
    Search for hotels in a destination for specific check-in and check-out dates.
    Returns recommended hotels, room options, and prices.
    """
    from tools.booking import search_hotels
    return search_hotels(destination, checkin_date, checkout_date, hotel_tier)

@tool
def book_hotel_tool(hotel_name: str, checkin_date: str, checkout_date: str, guest_name: str, price_per_night: float) -> str:
    """
    Book a hotel room in the specified hotel for guest with check-in and check-out dates.
    Returns booking receipt and confirmation ID.
    """
    from tools.booking import book_hotel
    return book_hotel(hotel_name, checkin_date, checkout_date, guest_name, price_per_night)

@tool
def get_map_url_tool(destination: str) -> str:
    """
    Get the OpenStreetMap embedding URL for a destination.
    Useful for displaying a map iframe of the travel region.
    """
    from tools.map import get_map_url
    return get_map_url(destination)

@tool
def set_itinerary_dashboard_data_tool(itinerary_json: str) -> str:
    """
    Save the structured trip itinerary details to the frontend visual dashboard.
    Call this tool whenever you have generated or updated a travel itinerary.
    The itinerary_json parameter MUST be a valid JSON string matching the TripItinerary schema.
    """
    # This confirmation will be returned to the agent and the JSON will update the graph state
    return "Itinerary data updated on the dashboard successfully."

# Collect all tools
ALL_TOOLS = [
    get_weather_tool,
    search_places_tool,
    convert_currency_tool,
    calculate_expenses_tool,
    search_tickets_tool,
    book_ticket_tool,
    search_hotels_tool,
    book_hotel_tool,
    get_map_url_tool,
    set_itinerary_dashboard_data_tool
]

# ---------------------------------------------------------
# LangGraph Workflow Construction
# ---------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    itinerary_data: Optional[str]

def build_workflow(api_key: Optional[str] = None):
    # Initialize Llama 3.1 70B model from Groq
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not configured. Please supply it via the environment or frontend input.")
        
    model = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=0.2,
        groq_api_key=key
    )
    
    # Bind tools to the model
    model_with_tools = model.bind_tools(ALL_TOOLS)
    
    # Node to execute the LLM call
    def call_model(state: AgentState):
        messages = state["messages"]
        
        # Add system prompt if it is the first turn
        if len(messages) == 1:
            system_prompt = SystemMessage(content=(
                "You are an expert AI Travel Planner Assistant. Your goal is to guide users to plan their trip, "
                "from identifying their route, starting points, and durations, to generating full detailed itineraries. "
                "Follow this protocol:\n"
                "1. If details are missing (like destination, starting point, number of days, budget level), ask the user clarifying questions.\n"
                "2. Utilize the weather tool to provide weather reports for the travel period.\n"
                "3. Utilize place search to recommend top tourist attractions, restaurants, and hotels.\n"
                "4. Calculate estimated costs using the expense tool and handle currency conversions with the currency tool if requested.\n"
                "5. Offer ticket and hotel searches, and perform bookings if the user asks to book. Inform them that bookings are simulated but confirmed.\n"
                "6. Provide the OpenStreetMap URL using the map tool so the UI can embed it.\n"
                "7. CRITICAL: Whenever you generate or update a full trip plan, you MUST call the `set_itinerary_dashboard_data_tool` with a "
                "fully populated JSON representation matching the `TripItinerary` schema. This displays the itinerary on the dashboard.\n"
                "Be polite, professional, structured, and informative. Format recommendations cleanly using Markdown."
            ))
            messages = [system_prompt] + list(messages)
            
        response = model_with_tools.invoke(messages)
        
        # Check if the model is invoking the set_itinerary_dashboard_data_tool
        itinerary_json = None
        if response.tool_calls:
            for tc in response.tool_calls:
                if tc["name"] == "set_itinerary_dashboard_data_tool":
                    itinerary_json = tc["args"].get("itinerary_json")
                    break
                    
        update_dict = {"messages": [response]}
        if itinerary_json:
            update_dict["itinerary_data"] = itinerary_json
            
        return update_dict
        
    # Router to determine transitions
    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END
        
    # Setup state graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )
    workflow.add_edge("tools", "agent")
    
    # Compile graph with checkpoints for memory saving
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)

# ---------------------------------------------------------
# Mock Itinerary JSON Builder (Fallback)
# ---------------------------------------------------------
def get_mock_itinerary_json(destination: str) -> str:
    dest = destination.lower()
    
    if "goa" in dest:
        title_prefix = "Goa Beach"
        theme1 = "Beach Vibe & Sunsets"
        theme2 = "Historical Heritage Tour"
        theme3 = "Water Adventures & Sports"
        theme4 = "Nature & Spice Trails"
        theme5 = "Relaxation & Departure"
        pack_list = ["Light cotton clothing", "Sunscreen (SPF 50+)", "Swimwear & sunglasses", "Beach sandals", "Comfortable walking shoes"]
        overview_text = "A perfect tropical gateway featuring historic churches, sun-kissed sandy beaches, spice plantations, and thrilling water adventure sports."
        visit_time = "November to February (Cooler weather, peak shack operations)"
        weather_text = "Sunny skies, average temperature of 29°C with gentle sea breeze."
        
        act1 = "Arrive in Goa, check-in to Baga beach hotel and unpack."
        act2 = "Relax on Baga sand, enjoy coconut water and watch paragliders."
        act3 = "Walk around Anjuna cliffs and watch the sunset over the Arabian sea."
        
        act4 = "Explore the UNESCO World Heritage basilica of Bom Jesus in Old Goa."
        act5 = "Visit Fort Aguada's 17th-century lighthouse and fortress."
        act6 = "Stroll the colorful Portuguese Latin Quarter in Fontainhas."
        
        act7 = "Boat trip to Grand Island with dolphin spotting on the route."
        act8 = "Snorkeling & Scuba diving in shallow reefs with certified guides."
        act9 = "Ayurvedic massage at a local beach resort, followed by Greek dinner at Thalassa."
        
        act10 = "Safari jeep ride inside Bhagwan Mahavir Sanctuary to Dudhsagar Waterfalls."
        act11 = "Tour Sahakari Spice Farm with Goan lunch cooked in fresh organic farm spices."
        act12 = "Shop cashew nuts, feni, and Goan spices at Panaji Market."
        
        act13 = "Stroll the serene Morjim beach, a turtle nesting conservation zone."
        act14 = "Check-out from hotel and transfer to Dabolim/Mopa airport."
        act15 = "Return flight departure back home."
    else:
        title_prefix = f"{destination.title()} Explore"
        theme1 = "Arrival & City Overview"
        theme2 = "Famous Sights & Monuments"
        theme3 = "Culinary Tour & Local Markets"
        theme4 = "Nature Walk & Views"
        theme5 = "Packing & Checkout"
        pack_list = ["Comfortable shoes", "Camera & Charger", "Weather-appropriate layers", "Travel adapters"]
        overview_text = f"An immersive travel itinerary showcasing the best of {destination.title()}'s culture, food, and sightseeing."
        visit_time = "Spring and Autumn (Mild weather and pleasant outdoor walks)"
        weather_text = "Clear skies, pleasant average temperature of 22°C."
        
        act1 = f"Land in {destination.title()}, hotel check-in and explore neighborhood."
        act2 = "Sightseeing central boulevard and local squares."
        act3 = "Dinner at a traditional local dining spot."
        
        act4 = "Guided historical tour of top central museums and landmarks."
        act5 = "Visit iconic panoramic observation deck."
        act6 = "Relaxing local garden or park walk."
        
        act7 = "Food tasting tour around central street market."
        act8 = "Boutique shopping and souvenir hunt."
        act9 = "Evening cultural performance or music show."
        
        act10 = "Nature hike or scenic drive in the outskirt valleys."
        act11 = "Lunch at a countryside retreat farm."
        act12 = "Visit local art gallery or craft studio."
        
        act13 = "Relaxing morning at hotel spa."
        act14 = "Pack bags and arrange transfer to terminal."
        act15 = "Board departure flight back home."

    itinerary_dict = {
        "destination": destination.title(),
        "duration_days": 5,
        "overview": overview_text,
        "best_time_to_visit": visit_time,
        "weather_forecast_summary": weather_text,
        "packing_checklist": pack_list,
        "daily_plans": [
            {
                "day_number": 1,
                "theme": theme1,
                "activities": [
                    {"time_of_day": "Morning", "activity_name": "Check-in & Settle", "description": act1, "suggested_meal": "Local cafe breakfast", "estimated_cost_usd": 15.0},
                    {"time_of_day": "Afternoon", "activity_name": "Explore Beach / Street", "description": act2, "suggested_meal": "Local street snacks", "estimated_cost_usd": 8.0},
                    {"time_of_day": "Evening", "activity_name": "Sunset Views", "description": act3, "suggested_meal": "Beachfront dinner", "estimated_cost_usd": 25.0}
                ]
            },
            {
                "day_number": 2,
                "theme": theme2,
                "activities": [
                    {"time_of_day": "Morning", "activity_name": "Heritage Walk", "description": act4, "suggested_meal": "Bakery treats & coffee", "estimated_cost_usd": 5.0},
                    {"time_of_day": "Afternoon", "activity_name": "Fort / Monument Tour", "description": act5, "suggested_meal": "Traditional lunch", "estimated_cost_usd": 15.0},
                    {"time_of_day": "Evening", "activity_name": "Cultural Walk", "description": act6, "suggested_meal": "Vindaloo/Authentic dinner", "estimated_cost_usd": 20.0}
                ]
            },
            {
                "day_number": 3,
                "theme": theme3,
                "activities": [
                    {"time_of_day": "Morning", "activity_name": "Island Trip / Tour", "description": act7, "suggested_meal": "Barbecue lunch", "estimated_cost_usd": 30.0},
                    {"time_of_day": "Afternoon", "activity_name": "Snorkeling / Sky Deck", "description": act8, "suggested_meal": "Fresh beverages", "estimated_cost_usd": 15.0},
                    {"time_of_day": "Evening", "activity_name": "Relaxing Lounge", "description": act9, "suggested_meal": "Greek / Sunset dinner", "estimated_cost_usd": 40.0}
                ]
            },
            {
                "day_number": 4,
                "theme": theme4,
                "activities": [
                    {"time_of_day": "Morning", "activity_name": "Waterfall / Valley Safari", "description": act10, "suggested_meal": "Packed buffet", "estimated_cost_usd": 25.0},
                    {"time_of_day": "Afternoon", "activity_name": "Spice Farm / Country Lunch", "description": act11, "suggested_meal": "Farm fresh lunch", "estimated_cost_usd": 10.0},
                    {"time_of_day": "Evening", "activity_name": "Market Shopping", "description": act12, "suggested_meal": "Traditional bistro dinner", "estimated_cost_usd": 15.0}
                ]
            },
            {
                "day_number": 5,
                "theme": theme5,
                "activities": [
                    {"time_of_day": "Morning", "activity_name": "Beach Stroll / Spa", "description": act13, "suggested_meal": "Pancakes & tea", "estimated_cost_usd": 10.0},
                    {"time_of_day": "Afternoon", "activity_name": "Checkout Preparation", "description": act14, "suggested_meal": "Quick cafe lunch", "estimated_cost_usd": 12.0},
                    {"time_of_day": "Evening", "activity_name": "Airport Boarding", "description": act15, "suggested_meal": "Lounge snacks", "estimated_cost_usd": 0.0}
                ]
            }
        ],
        "budget_breakdown": [
            {"category": "Accommodation", "estimated_cost_usd": 300.0, "notes": "Standard hotel stay charges"},
            {"category": "Food", "estimated_cost_usd": 140.0, "notes": "Meals at local diners and shacks"},
            {"category": "Activities", "estimated_cost_usd": 125.0, "notes": "Safari entries, rentals, and tours"},
            {"category": "Transport", "estimated_cost_usd": 50.0, "notes": "Local cabs or scooter rentals"},
            {"category": "Miscellaneous", "estimated_cost_usd": 35.0, "notes": "Guides and minor purchases"}
        ],
        "general_travel_tips": [
            {"title": "Local Transport", "details": "Renting a gearless scooter or bicycle is the best way to get around local sight locations."},
            {"title": "Card vs Cash", "details": "UPI/Cards are widely used, but keep some cash handy for street markets and guides."}
        ]
    }
    return json.dumps(itinerary_dict)

# ---------------------------------------------------------
# Run Execution Wrapper
# ---------------------------------------------------------
def run_agent(query: str, thread_id: str, groq_api_key: Optional[str] = None) -> dict:
    """
    Invokes the LangGraph compiled state graph with a query.
    Maintains memory context via thread_id.
    Returns a dictionary with response text and itinerary dashboard data.
    """
    try:
        app = build_workflow(api_key=groq_api_key)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the graph
        events = app.invoke(
            {"messages": [HumanMessage(content=query)]},
            config
        )
        
        # Extract the last message from the run
        last_message = events["messages"][-1]
        
        return {
            "response": last_message.content,
            "itinerary_data": events.get("itinerary_data")
        }
    except Exception as e:
        # Fallback to Mock Travel Agent when Groq API key is missing or invalid
        q_lower = query.lower()
        
        # Extract destination
        destination = "goa"
        if "tokyo" in q_lower:
            destination = "tokyo"
        elif "paris" in q_lower:
            destination = "paris"
        elif "rome" in q_lower:
            destination = "rome"
        elif "delhi" in q_lower:
            destination = "delhi"
            
        mock_itinerary = get_mock_itinerary_json(destination)
        
        if "weather" in q_lower:
            from tools.weather import get_weather
            return {
                "response": f"🤖 **[Mock Agent Fallback]** {get_weather(destination)}",
                "itinerary_data": None
            }
            
        elif "book" in q_lower or "ticket" in q_lower or "hotel" in q_lower:
            from tools.booking import search_tickets, book_ticket, search_hotels, book_hotel
            if "hotel" in q_lower:
                if "option" in q_lower or "confirm" in q_lower or "reserve" in q_lower:
                    return {
                        "response": f"🤖 **[Mock Agent Fallback]**\n\n{book_hotel('Fairfield by Marriott', '2026-06-25', '2026-06-28', 'Guest User', 6500)}",
                        "itinerary_data": None
                    }
                else:
                    return {
                        "response": f"🤖 **[Mock Agent Fallback]**\n\n{search_hotels(destination, '2026-06-25', '2026-06-28')}",
                        "itinerary_data": None
                    }
            else:
                if "option" in q_lower or "confirm" in q_lower or "reserve" in q_lower:
                    return {
                        "response": f"🤖 **[Mock Agent Fallback]**\n\n{book_ticket('Delhi', 'Goa', '2026-06-25', 'IndiGo (6E-2015)', 5500, 'Passenger User')}",
                        "itinerary_data": None
                    }
                else:
                    return {
                        "response": f"🤖 **[Mock Agent Fallback]**\n\n{search_tickets('Delhi', destination, '2026-06-25', 'Flight')}",
                        "itinerary_data": None
                    }
                    
        elif "budget" in q_lower or "expense" in q_lower or "cost" in q_lower or "calculator" in q_lower or "price" in q_lower:
            from tools.expense import calculate_expenses
            return {
                "response": f"🤖 **[Mock Agent Fallback]**\n\n{calculate_expenses(destination, 5, 'Moderate', 'Couple')}",
                "itinerary_data": mock_itinerary
            }
            
        elif "map" in q_lower:
            from tools.map import get_map_url
            url = get_map_url(destination)
            return {
                "response": f"🤖 **[Mock Agent Fallback]** Here is the interactive route map for {destination.title()}:\n\n({url})",
                "itinerary_data": None
            }
            
        else:
            from tools.weather import get_weather
            from tools.search import search_places
            from tools.expense import calculate_expenses
            from tools.map import get_map_url
            
            weather_info = get_weather(destination)
            places_info = search_places(destination)
            budget_info = calculate_expenses(destination, 5, "Moderate", "Couple")
            map_info = get_map_url(destination)
            
            response_text = f"""
🤖 **[Mock Agent Fallback]** Here is your personalized travel plan for a 5-Day trip to **{destination.title()}**:

### ☀️ Weather Status
{weather_info}

### 🗺️ OpenStreetMap Route Map
Map embed URL: ({map_info})

### 📅 Itinerary Overview
- **Day 1: Arrival & Local Walk**
  Explore nearby markets and cafes.
- **Day 2: Historical Tour**
  Visit top monuments, sights, and historical buildings.
- **Day 3: Scenic Lookout & Hiking**
  Enjoy natural beauty, viewpoints, and photo points.
- **Day 4: Adventure Activities**
  Local water sports, treks, or shopping excursions.
- **Day 5: Souvenirs & Departure**
  Packing, checking out, and airport drop.

### 🏛️ Place Recommendations & Attractions
{places_info}

### 💰 Expense Calculator Summary
{budget_info}

*How can I help you customize this? You can tell me to book flights, search hotels, check currency rates, or show local map details.*
""".strip()
            return {
                "response": response_text,
                "itinerary_data": mock_itinerary
            }
