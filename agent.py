"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import load_wardrobe_schema, get_empty_wardrobe
import os
from dotenv import load_dotenv
from groq import Groq
import json

EXAMPLE_JSON = {
    "description": "vintage graphic tee",
    "size": "M",
    "max_price": 30.0,
    "wardrobe": {
        "items": [
            {
                "id": "w_001",
                "name": "baggy pants",
                "category": "bottoms",
                "colors": [],
                "style_tags": ["baggy"],
                "notes": ""
            },
            {
                "id": "w_002",
                "name": "chunky sneakers",
                "category": "shoes",
                "colors": [],
                "style_tags": ["chunky"],
                "notes": ""
            }
        ]
    }
}

SYSTEM_PROMPT = (
    "From the query, extract the following information:\n"
    "1. The item the user wants as a JSON object with fields `description` (str), `size` (str), `max_price` (float)\n"
    f"2. The wardrobe the user has which should be formatted like {load_wardrobe_schema()}"
    "\nReturn both of these as a single JSON object."
    "Do not output anything else besides this JSON object. Use double quotes only. If no price or size is specified, use None as the value."
    "\nExample Input: I'm looking for a vintage graphic tee under $30, size M. I mostly wear baggy jeans and chunky sneakers."
    f"\nExample Output: {EXAMPLE_JSON}"
)

MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────
load_dotenv()

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)

# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """

    session = _new_session(query, wardrobe)

    GROQ_CLIENT = _get_groq_client()

    response = GROQ_CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        temperature=0.0,
    )

    QUERY_JSON_STR = response.choices[0].message.content
    QUERY_JSON = json.loads(QUERY_JSON_STR)

    session['parsed'] = {
        "description": QUERY_JSON['description'], 
        "size": QUERY_JSON['size'], 
        "max_price": QUERY_JSON['max_price']
    }

    session["search_results"] = search_listings(
        description=session['parsed']['description'],
        size=session['parsed']['size'],
        max_price=session['parsed']['max_price'] 
    )

    if not session["search_results"]:
        session["error"] = "Unfortunately, no listings matched your query. Try loosening your search or asking for a different item."
        return session
    
    session['selected_item'] = session["search_results"][0]

    session['wardrobe'] = QUERY_JSON['wardrobe'] if wardrobe == get_empty_wardrobe() else wardrobe

    outfit = suggest_outfit(new_item=session['selected_item'], wardrobe=session['wardrobe'])
    session['outfit_suggestion'] = outfit

    fit_card = create_fit_card(outfit=session['outfit_suggestion'], new_item=session['selected_item'])
    session["fit_card"] = fit_card

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    # run_agent(
    #     "I'm looking for a faded pair of jeans, W30, to go with my white tank top and black jacket.", 
    #     get_empty_wardrobe()
    # )
