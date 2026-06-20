def get_map_url(destination: str) -> str:
    """
    Get the OpenStreetMap embedding URL for a destination.
    Useful for displaying a map iframe of the travel region.
    """
    dest = destination.lower()
    
    # Bounding boxes for OpenStreetMap embeds
    # Format: bbox=min_lon,min_lat,max_lon,max_lat
    if "goa" in dest:
        # Bounding box covering North and South Goa
        return "https://www.openstreetmap.org/export/embed.html?bbox=73.682%2C14.887%2C74.341%2C15.827&layer=mapnik"
    elif "tokyo" in dest:
        # Bounding box covering central Tokyo
        return "https://www.openstreetmap.org/export/embed.html?bbox=139.601%2C35.582%2C139.854%2C35.751&layer=mapnik"
    elif "paris" in dest:
        # Bounding box covering central Paris
        return "https://www.openstreetmap.org/export/embed.html?bbox=2.213%2C48.815%2C2.434%2C48.902&layer=mapnik"
    elif "rome" in dest:
        # Bounding box covering central Rome
        return "https://www.openstreetmap.org/export/embed.html?bbox=12.425%2C41.852%2C12.562%2C41.938&layer=mapnik"
    elif "delhi" in dest:
        # Bounding box covering Delhi
        return "https://www.openstreetmap.org/export/embed.html?bbox=77.015%2C28.485%2C77.348%2C28.745&layer=mapnik"
    else:
        # Bounding box of the world
        return "https://www.openstreetmap.org/export/embed.html?bbox=-180%2C-60%2C180%2C80&layer=mapnik"
