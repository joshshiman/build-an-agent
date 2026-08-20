from ibm_watsonx_orchestrate.agent_builder.tools import tool

# A small catalog of venue "templates" adapted to whatever city is asked about.
VENUE_TEMPLATES = [
    {"suffix": "Community Hall",  "capacity": 40,  "price": 500,  "style": "simple and budget-friendly"},
    {"suffix": "Rooftop Lounge",  "capacity": 60,  "price": 1500, "style": "trendy with skyline views"},
    {"suffix": "Garden Pavilion", "capacity": 120, "price": 2500, "style": "outdoor and scenic"},
    {"suffix": "Grand Ballroom",  "capacity": 300, "price": 6000, "style": "elegant and formal"},
    {"suffix": "Co-working Loft", "capacity": 30,  "price": 800,  "style": "modern, great for teams"},
]


@tool
def suggest_venues(city: str, num_guests: int, max_budget: float) -> dict:
    """Suggest event venues in a city that fit the guest count and rental budget.

    Use this tool when the user wants venue ideas and has told you the city,
    roughly how many guests, and how much they can spend on the space.

    Args:
        city: The city to look for venues in.
        num_guests: The number of guests the venue must hold.
        max_budget: The maximum venue rental budget in USD.

    Returns:
        A dictionary with a list of matching venues, cheapest first.
    """
    matches = [
        {
            "name": f"The {city} {t['suffix']}",
            "capacity": t["capacity"],
            "price_usd": t["price"],
            "style": t["style"],
        }
        for t in VENUE_TEMPLATES
        if t["capacity"] >= num_guests and t["price"] <= max_budget
    ]
    matches.sort(key=lambda v: v["price_usd"])
    if matches:
        msg = f"Found {len(matches)} venue(s) in {city} for {num_guests} guests under ${max_budget:.0f}."
    else:
        msg = f"No venues in {city} fit {num_guests} guests under ${max_budget:.0f}. Try a higher budget."
    return {"city": city, "message": msg, "venues": matches}
