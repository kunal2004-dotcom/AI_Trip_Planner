from typing import Dict, List, Any

def calculate_expenses(
    destination: str,
    days: int,
    budget_tier: str,
    travel_group: str
) -> str:
    """
    Calculate and estimate total travel expenses based on destination, days, budget tier, and travel group.
    Returns a categorized cost breakdown in USD and INR.
    """
    bt = budget_tier.lower()
    group = travel_group.lower()
    
    # Establish base multipliers
    group_multiplier = 1.0
    if "couple" in group:
        group_multiplier = 1.8
    elif "family" in group:
        group_multiplier = 3.0
    elif "friends" in group:
        group_multiplier = 4.0
        
    # Cost per day per person/unit
    if "luxury" in bt:
        stay_cost = 250.0
        food_cost = 70.0
        local_transport = 50.0
        activities = 60.0
    elif "moderate" in bt:
        stay_cost = 90.0
        food_cost = 35.0
        local_transport = 20.0
        activities = 25.0
    else:  # Economy
        stay_cost = 30.0
        food_cost = 15.0
        local_transport = 8.0
        activities = 10.0

    # Adjust based on destination
    dest_lower = destination.lower()
    dest_multiplier = 1.0
    if "tokyo" in dest_lower or "japan" in dest_lower:
        dest_multiplier = 1.4
    elif "paris" in dest_lower or "france" in dest_lower:
        dest_multiplier = 1.5
    elif "rome" in dest_lower or "italy" in dest_lower:
        dest_multiplier = 1.3
    elif "goa" in dest_lower or "india" in dest_lower:
        dest_multiplier = 0.5
        
    stay_total = stay_cost * days * group_multiplier * dest_multiplier
    food_total = food_cost * days * group_multiplier * dest_multiplier
    transport_total = local_transport * days * group_multiplier * dest_multiplier
    activities_total = activities * days * group_multiplier * dest_multiplier
    misc_total = 15.0 * days * group_multiplier * dest_multiplier
    
    total_usd = stay_total + food_total + transport_total + activities_total + misc_total
    total_inr = total_usd * 83.50
    
    breakdown = f"""
Trip Budget Breakdown for {days} days in {destination} ({budget_tier}, {travel_group}):

1. Accommodation: ${stay_total:.2f} (~₹{stay_total * 83.50:.0f})
   - Notes: Estimated based on standard rooms for {travel_group} in {destination}.
2. Food & Dining: ${food_total:.2f} (~₹{food_total * 83.50:.0f})
   - Notes: Three meals a day plus local snacks.
3. Local Transport: ${transport_total:.2f} (~₹{transport_total * 83.50:.0f})
   - Notes: Covers cabs, metro cards, or local scooter/car rental.
4. Activities & Entry Fees: ${activities_total:.2f} (~₹{activities_total * 83.50:.0f})
   - Notes: Covers standard tours, museum entries, and water sports.
5. Miscellaneous: ${misc_total:.2f} (~₹{misc_total * 83.50:.0f})
   - Notes: SIM cards, emergency cash, and tips.

-------------------------------------------------
TOTAL ESTIMATED COST: ${total_usd:.2f} (~₹{total_inr:.2f})
"""
    return breakdown.strip()
