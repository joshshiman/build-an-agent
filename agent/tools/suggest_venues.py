from ibm_watsonx_orchestrate.agent_builder.tools import tool


# A small catalog of venue "templates". Each one is turned into a real suggestion
# for whatever city the user asks about, so the tool needs no external data source.
VENUE_TEMPLATES = [
    {"suffix": "Community Hall",   "capacity": 40,  "price": 500,  "style": "simple and budget-friendly"},
    {"suffix": "Rooftop Lounge",   "capacity": 60,  "price": 1500, "style": "trendy with skyline views"},
    {"suffix": "Garden Pavilion",  "capacity": 120, "price": 2500, "style": "outdoor and scenic"},
    {"suffix": "Grand Ballroom",   "capacity": 300, "price": 6000, "style": "elegant and formal"},
    {"suffix": "Co-working Loft",  "capacity": 30,  "price": 800,  "style": "modern, great for team events"},
]


@tool
def suggest_venues(city: str, num_guests: int, max_budget: float) -> dict:
    """Suggest event venues in a city that fit the guest count and rental budget.

    Use this tool when the user wants venue ideas for their event and has told you
    the city, roughly how many guests, and how much they can spend on the space.

    Args:
        city: The city to look for venues in.
        num_guests: The number of guests the venue must be able to hold.
        max_budget: The maximum venue rental budget in US dollars.

    Returns:
        A dictionary with a list of matching venues (name, capacity, price, style).
        If nothing fits, the list is empty and a message explains why.
    """
    matches = []
    for template in VENUE_TEMPLATES:
        if template["capacity"] >= num_guests and template["price"] <= max_budget:
            matches.append({
                "name": f"The {city} {template['suffix']}",
                "capacity": template["capacity"],
                "price_usd": template["price"],
                "style": template["style"],
            })

    # Show the most affordable options first.
    matches.sort(key=lambda v: v["price_usd"])

    message = (
        f"Found {len(matches)} venue(s) in {city} for {num_guests} guests "
        f"under ${max_budget:.0f}."
    )
    if not matches:
        message = (
            f"No venues in {city} fit {num_guests} guests under ${max_budget:.0f}. "
            "Try raising the budget or lowering the guest count."
        )

    return {"city": city, "message": message, "venues": matches}
