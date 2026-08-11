from ibm_watsonx_orchestrate.agent_builder.tools import tool


# Rough per-guest cost (in USD) for each event type, broken out by category.
# These are made-up planning estimates so the tool works with no external API.
EVENT_COSTS = {
    "birthday party": {"catering": 25, "drinks": 10, "decorations": 8, "entertainment": 12},
    "team offsite":   {"catering": 40, "drinks": 12, "decorations": 5, "entertainment": 20},
    "wedding":        {"catering": 90, "drinks": 35, "decorations": 30, "entertainment": 45},
    "conference":     {"catering": 35, "drinks": 8,  "decorations": 6,  "entertainment": 15},
    "casual gathering": {"catering": 15, "drinks": 8, "decorations": 4, "entertainment": 5},
}

# Fallback used when the event type isn't one we recognize.
DEFAULT_COSTS = {"catering": 30, "drinks": 12, "decorations": 8, "entertainment": 15}


@tool
def estimate_event_budget(num_guests: int, event_type: str) -> dict:
    """Estimate a cost breakdown for an event based on guest count and event type.

    Use this tool whenever the user wants to know roughly how much an event will
    cost, or gives a guest count and an event type.

    Args:
        num_guests: The number of people expected to attend.
        event_type: The kind of event, for example "birthday party", "team offsite",
            "wedding", "conference", or "casual gathering".

    Returns:
        A dictionary with the per-category costs (venue, catering, drinks,
        decorations, entertainment) and the estimated total in US dollars.
    """
    per_guest = EVENT_COSTS.get(event_type.strip().lower(), DEFAULT_COSTS)

    breakdown = {category: cost * num_guests for category, cost in per_guest.items()}

    # A simple venue estimate that scales in steps with the size of the party.
    breakdown["venue"] = 300 + 15 * num_guests

    total = sum(breakdown.values())

    return {
        "event_type": event_type,
        "num_guests": num_guests,
        "breakdown_usd": breakdown,
        "estimated_total_usd": total,
    }
