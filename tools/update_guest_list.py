from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def update_guest_list(current_guests: list, action: str, names: list) -> dict:
    """Add or remove names from an event guest list and return the updated list.

    This tool does not remember anything between calls: pass the current guest
    list in every time (use an empty list to start fresh). Use it whenever the
    user wants to add guests, remove guests, or count the people on the list.

    Args:
        current_guests: The guest names already on the list. Pass [] to start.
        action: What to do -- either "add" or "remove".
        names: The guest names to add or remove.

    Returns:
        A dictionary with the updated guest list and the total guest count.
    """
    guests = list(current_guests)
    action = action.strip().lower()
    if action == "add":
        for name in names:
            if name not in guests:
                guests.append(name)
    elif action == "remove":
        guests = [g for g in guests if g not in names]
    else:
        return {"error": f"Unknown action '{action}'. Use 'add' or 'remove'.",
                "guest_list": guests, "total_guests": len(guests)}
    return {"guest_list": guests, "total_guests": len(guests)}
