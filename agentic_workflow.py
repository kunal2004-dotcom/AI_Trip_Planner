import os
from typing import TypedDict, Annotated, Sequence, Optional
from dotenv import load_dotenv

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
    get_map_url_tool
]

# ---------------------------------------------------------
# LangGraph Workflow Construction
# ---------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

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
                "Be polite, professional, structured, and informative. Format recommendations cleanly using Markdown."
            ))
            messages = [system_prompt] + list(messages)
            
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}
        
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
# Run Execution Wrapper
# ---------------------------------------------------------
def run_agent(query: str, thread_id: str, groq_api_key: Optional[str] = None) -> str:
    """
    Invokes the LangGraph compiled state graph with a query.
    Maintains memory context via thread_id.
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
        return last_message.content
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
            
        if "weather" in q_lower:
            from tools.weather import get_weather
            return f"🤖 **[Mock Agent Fallback]** {get_weather(destination)}"
            
        elif "book" in q_lower or "ticket" in q_lower or "hotel" in q_lower:
            from tools.booking import search_tickets, book_ticket, search_hotels, book_hotel
            if "hotel" in q_lower:
                if "option" in q_lower or "confirm" in q_lower or "reserve" in q_lower:
                    return f"🤖 **[Mock Agent Fallback]**\n\n{book_hotel('Fairfield by Marriott', '2026-06-25', '2026-06-28', 'Guest User', 6500)}"
                else:
                    return f"🤖 **[Mock Agent Fallback]**\n\n{search_hotels(destination, '2026-06-25', '2026-06-28')}"
            else:
                if "option" in q_lower or "confirm" in q_lower or "reserve" in q_lower:
                    return f"🤖 **[Mock Agent Fallback]**\n\n{book_ticket('Delhi', 'Goa', '2026-06-25', 'IndiGo (6E-2015)', 5500, 'Passenger User')}"
                else:
                    return f"🤖 **[Mock Agent Fallback]**\n\n{search_tickets('Delhi', destination, '2026-06-25', 'Flight')}"
                    
        elif "budget" in q_lower or "expense" in q_lower or "cost" in q_lower or "calculator" in q_lower or "price" in q_lower:
            from tools.expense import calculate_expenses
            return f"🤖 **[Mock Agent Fallback]**\n\n{calculate_expenses(destination, 5, 'Moderate', 'Couple')}"
            
        elif "map" in q_lower:
            from tools.map import get_map_url
            url = get_map_url(destination)
            return f"🤖 **[Mock Agent Fallback]** Here is the interactive route map for {destination.title()}:\n\n({url})"
            
        else:
            from tools.weather import get_weather
            from tools.search import search_places
            from tools.expense import calculate_expenses
            from tools.map import get_map_url
            
            weather_info = get_weather(destination)
            places_info = search_places(destination)
            budget_info = calculate_expenses(destination, 5, "Moderate", "Couple")
            map_info = get_map_url(destination)
            
            return f"""
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
