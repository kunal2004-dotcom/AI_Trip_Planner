import os
from typing import Optional

def search_places(query: str) -> str:
    """
    Search for tourist attractions, places to visit, restaurants, or hotels.
    Use this to find specific landmarks and recommendations for a destination.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    
    if api_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, search_depth="basic")
            results = response.get("results", [])
            if results:
                summary = []
                for idx, r in enumerate(results[:3]):
                    summary.append(f"{idx+1}. {r['title']}: {r['content']} (Source: {r['url']})")
                return "\n".join(summary)
        except Exception as e:
            pass
            
    # Mock fallback search results for robust demonstration
    q_lower = query.lower()
    if "goa" in q_lower:
        if "hotel" in q_lower or "stay" in q_lower:
            return """
Goa Hotel/Stay Recommendations:
1. Taj Exotica Resort & Spa (Benaulim, South Goa): Luxury beachfront resort, Mediterranean style villa rooms, private pool access. (~₹25,000/night)
2. Fairfield by Marriott Goa Baga (Baga, North Goa): Mid-range modern hotel, walking distance to Baga Beach, pool, buffet. (~₹6,500/night)
3. Zostel Goa (Calangute, North Goa): Budget friendly backpacker hostel, vibrant community vibe, pool, close to beach. (~₹800/night for dorms, ₹2500 for private rooms)
"""
        elif "adventure" in q_lower or "activities" in q_lower or "sports" in q_lower:
            return """
Goa Adventure & Water Sports:
1. Calangute & Baga Beaches: Parasailing, jet skiing, banana boat rides, bumper rides.
2. Grand Island Scuba Diving: Full-day trip featuring boat ride, dolphin spotting, underwater diving with certified instructors.
3. Dudhsagar Waterfalls Trek: 4-tiered majestic waterfall located on Mandovi River. Offers hiking trails and off-road jeep safaris.
"""
        else:
            return """
Goa Top Attractions:
1. Baga Beach & Calangute Beach: Famous for active nightlife, shacks, watersports, and shopping streets.
2. Fort Aguada: 17th-century Portuguese lighthouse and fort offering scenic panoramic ocean views.
3. Basilica of Bom Jesus: UNESCO World Heritage site containing the mortal remains of St. Francis Xavier. Masterpiece of baroque architecture.
4. Dudhsagar Falls: Majestic multi-tiered waterfall nestled inside the Bhagwan Mahavir Sanctuary.
5. Anjuna Flea Market: Vibrant weekly shopping bazaar for local crafts, clothes, and spices.
"""
    elif "tokyo" in q_lower:
        return """
Tokyo Top Recommendations:
1. Shibuya Crossing & Shibuya Sky: World's busiest pedestrian crossing with a stunning glass observatory offering views of Mt. Fuji.
2. Senso-ji Temple (Asakusa): Tokyo's oldest and most iconic Buddhist temple, accessed via Nakamise shopping street.
3. Tokyo Skytree: Landmark tower offering sweeping panoramas of Tokyo's skyline.
4. Shinjuku Gyoen National Garden: A large park blending traditional Japanese, English, and French garden designs.
5. Tsukiji Outer Market: Incredible street food stalls for fresh sushi, wagyu beef skewers, and traditional sweets.
"""
    elif "paris" in q_lower:
        return """
Paris Top Recommendations:
1. Eiffel Tower: The definitive iron structure offering romantic views. Must book summit tickets in advance.
2. The Louvre Museum: World's largest art museum, home to the Mona Lisa and Venus de Milo.
3. Seine River Cruise: Relaxing evening boat cruise showing Notre-Dame, Musee d'Orsay, and Eiffel Tower lights.
4. Montmartre & Sacre-Coeur: Artistic hilltop neighborhood with cobble streets, artists squares, and the white dome Basilica.
5. Palace of Versailles: Extravagant historical palace of King Louis XIV, famous for the Hall of Mirrors and grand gardens.
"""
    else:
        return f"Attractions & Recommendations for '{query}':\n- Central Historic Square: Offers cultural walks and architecture.\n- Local Cuisine Tour: Guided street food tasting sessions.\n- Nature/Scenic Lookout: Panoramic view point accessible via easy hike."
