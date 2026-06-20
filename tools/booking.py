import random
from typing import Dict, Any

def search_tickets(from_location: str, to_location: str, travel_date: str, vehicle_type: str = "Flight") -> str:
    """
    Search for travel tickets (Flight, Train, or Bus) from a starting location to a destination on a given date.
    Returns list of options, departure times, and prices.
    """
    vt = vehicle_type.lower().strip()
    from_loc = from_location.title()
    to_loc = to_location.title()
    
    if "flight" in vt:
        options = [
            {"carrier": "IndiGo", "flight_no": "6E-2015", "dep_time": "08:15 AM", "arr_time": "10:45 AM", "price_inr": 5500},
            {"carrier": "Air India", "flight_no": "AI-883", "dep_time": "01:30 PM", "arr_time": "04:00 PM", "price_inr": 6200},
            {"carrier": "Vistara", "flight_no": "UK-825", "dep_time": "06:45 PM", "arr_time": "09:15 PM", "price_inr": 7000}
        ]
    elif "train" in vt:
        options = [
            {"carrier": "Rajdhani Express", "train_no": "12424", "dep_time": "04:30 PM", "arr_time": "02:00 PM (Next Day)", "price_inr": 3400},
            {"carrier": "Garib Rath", "train_no": "12210", "dep_time": "09:00 AM", "arr_time": "07:30 AM (Next Day)", "price_inr": 1200},
            {"carrier": "Duronto Express", "train_no": "12260", "dep_time": "11:50 PM", "arr_time": "09:30 PM (Next Day)", "price_inr": 2800}
        ]
    else:  # Bus
        options = [
            {"carrier": "Paulo Travels (AC Sleeper)", "bus_no": "GA-03-A-1234", "dep_time": "08:00 PM", "arr_time": "08:30 AM (Next Day)", "price_inr": 1500},
            {"carrier": "Atmaram Travels (Scania Multi-Axle)", "bus_no": "MH-09-Q-7788", "dep_time": "09:30 PM", "arr_time": "10:00 AM (Next Day)", "price_inr": 1800}
        ]
        
    result_str = f"Available {vehicle_type.capitalize()} tickets from {from_loc} to {to_loc} on {travel_date}:\n"
    for idx, opt in enumerate(options):
        if "flight_no" in opt:
            no = opt["flight_no"]
        elif "train_no" in opt:
            no = opt["train_no"]
        else:
            no = opt["bus_no"]
            
        result_str += f"- Option {idx+1}: {opt['carrier']} ({no}) | Departs: {opt['dep_time']} -> Arrives: {opt['arr_time']} | Price: ₹{opt['price_inr']}\n"
        
    result_str += f"\nTo book an option, tell the chatbot: 'Book Option X for Passenger Name'."
    return result_str.strip()

def book_ticket(from_location: str, to_location: str, travel_date: str, carrier: str, price_inr: float, passenger_name: str) -> str:
    """
    Book a travel ticket for a passenger on a specific carrier from starting location to destination.
    Returns confirmation details including Ticket PNR and seat number.
    """
    pnr = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
    seat = f"{random.randint(1, 30)}{random.choice('ABCDEF')}"
    
    confirmation = f"""
🎟️ TICKET BOOKING CONFIRMED!
---------------------------------------------
PNR / Booking ID: {pnr}
Passenger: {passenger_name}
Route: {from_location.title()} -> {to_location.title()}
Date of Travel: {travel_date}
Carrier / Vehicle: {carrier}
Allocated Seat: {seat}
Total Amount Paid: ₹{price_inr:.2f}
Status: CONFIRMED

Note: Your electronic ticket details have been simulated and registered in the app.
"""
    return confirmation.strip()

def search_hotels(destination: str, checkin_date: str, checkout_date: str, hotel_tier: str = "Moderate") -> str:
    """
    Search for hotels in a destination for specific check-in and check-out dates.
    Returns recommended hotels, room options, and prices.
    """
    dest = destination.title()
    tier = hotel_tier.lower()
    
    if "luxury" in tier:
        hotels = [
            {"name": "The Leela Palace Resort", "rating": "4.9/5", "price_per_night": 22000, "room_type": "Sea View Suite"},
            {"name": "Taj Exotica Hotel", "rating": "4.8/5", "price_per_night": 25000, "room_type": "Garden Villa Room"}
        ]
    elif "budget" in tier or "economy" in tier:
        hotels = [
            {"name": "RedDoorz Cozy Inn", "rating": "4.1/5", "price_per_night": 1800, "room_type": "Standard AC Room"},
            {"name": "Zostel Hostel Rooms", "rating": "4.3/5", "price_per_night": 900, "room_type": "Deluxe Dorm Bed"}
        ]
    else:  # Moderate
        hotels = [
            {"name": "Fairfield by Marriott", "rating": "4.5/5", "price_per_night": 6500, "room_type": "Superior King Room"},
            {"name": "Lemon Tree Amarante Beach Resort", "rating": "4.4/5", "price_per_night": 5200, "room_type": "Heritage Pavilion Room"}
        ]
        
    result_str = f"Recommended hotels in {dest} from {checkin_date} to {checkout_date} ({hotel_tier} tier):\n"
    for idx, h in enumerate(hotels):
        result_str += f"- Option {idx+1}: {h['name']} ({h['rating']}) | Room: {h['room_type']} | Price: ₹{h['price_per_night']}/night\n"
        
    result_str += f"\nTo book a hotel room, tell the chatbot: 'Book Hotel Option X for Guest Name'."
    return result_str.strip()

def book_hotel(hotel_name: str, checkin_date: str, checkout_date: str, guest_name: str, price_per_night: float) -> str:
    """
    Book a hotel room in the specified hotel for guest with check-in and check-out dates.
    Returns booking receipt and confirmation ID.
    """
    booking_id = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=8))
    room_no = random.randint(101, 509)
    days = 3 # Default length
    total_price = price_per_night * days
    
    receipt = f"""
🏨 HOTEL ROOM BOOKING CONFIRMED!
---------------------------------------------
Booking Reference ID: {booking_id}
Guest Name: {guest_name}
Hotel: {hotel_name}
Stay Duration: {checkin_date} to {checkout_date} ({days} Nights)
Allocated Room: Room {room_no} (AC Deluxe)
Price per Night: ₹{price_per_night:.2f}
Total Charges: ₹{total_price:.2f} (Paid via simulated wallet)
Status: RESERVED & CONFIRMED

Note: Bring this Booking ID during check-in.
"""
    return receipt.strip()
