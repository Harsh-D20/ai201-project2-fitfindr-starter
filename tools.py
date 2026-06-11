"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import string

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    
    # load all listings
    all_listings = load_listings()

    # filter listings by price and size
    if max_price == None:
        max_price = float('inf')

    size = size.lower() if size != None else None
    filtered_listings = []

    for listing in all_listings:
        if listing['price'] <= max_price:
            if 'one size' in listing['size'].lower():
                filtered_listings.append(listing)
                continue
            
            # tops are specified with letters (S, M, L, XL), one listing can have multiple sizes separated by '/'
            top_sizes = listing['size'].lower().split('/')
            # bottoms are specifed with either Waist, Length, or both with a number (e.g. W32, L30, W30 L30)
            bottom_sizes = listing['size'].lower().split(" ")
            # shoes are specified with country and number (e.g. US 8), actually gets caught in other two checks
            # other sizes are: "One Size", "Adjustable", "One Size Fits Most", etc. This should match any query
            
            if size == None or size in top_sizes or size in bottom_sizes:
                filtered_listings.append(listing)


    # score listings by keyword overlap with description and title
    keywords = set(description.lower().split())
    scored_listings = []
    for listing in filtered_listings:
        # create the set of words from description
        # Remove punctuation using translate
        translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
        clean_desc = listing['description'].lower().translate(translator)
        # consider adding title into match keywords.
        clean_title = listing['title'].lower().translate(translator)
        listing_kw = set(clean_title.split() + clean_desc.split())

        # calculate score between listing and description
        score = len(keywords.intersection(listing_kw))
        if score > 0:
            scored_listings.append((score, listing))

    # keep as backup for later if we want to do this
    # sort by score (highest first), then by price (lowest/cheapest first) to break ties
    # scored_listings.sort(key=lambda x: (-x[0], x[1]['price']))

    scored_listings.sort(key=lambda x: -x[0])

    return [listing for _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """

    PROMPT_BASE = "You are a stylist helping me put together outfits. I am considering buying the following thrifted item:\n" \
    f"{new_item['title']}\n- {new_item['description']}\n- Category: {new_item['category']}\n- Style tags: {', '.join(new_item['style_tags'])}\n- Size: {new_item['size']}\n- Condition: {new_item['condition']}\n- Colors: {', '.join(new_item['colors'])}\n- Brand: {new_item['brand']}\n\n"

    wardrobe_prompt = ""

    # empty wardrobe
    if wardrobe['items'] == []:
        wardrobe_prompt = "Provide 1-2 sentences of general styling advice for how to wear the item, what kinds of pieces it pairs well with, and what vibe it suits."

    else:
        wardrobe_prompt = "My current wardrobe includes the folllowing items: \n"
    
        for item in wardrobe['items']:
            wardrobe_prompt += f"- {item['name']} (Category: {item['category']}), Color(s): {', '.join(item['colors'])}, Style tags: {', '.join(item['style_tags'])}, Notes: {item['notes']}\n"

        wardrobe_prompt += "\nBased on the thrifted item and my wardrobe, suggest one outfit combination that incorporates the thrifted item and pieces from my wardrobe. Describe the outfit in 1-2 sentences."
        
    FINAL_PROMPT = PROMPT_BASE + wardrobe_prompt
    
    GROQ_CLIENT = _get_groq_client()

    response = GROQ_CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": FINAL_PROMPT}
        ],
        temperature=0.5,
    )

    message = response.choices[0].message.content

    return message

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2-4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit.strip():
        return "ERROR: Outfit suggestion is empty. Cannot create fit card without an outfit."

    PROMPT = f"You are a fashion influencer helping an Instagram and/or TikTok caption for an Outfit of the Day (OOTD) post." \
        " You have created an outfit by combining what's in your wardrobe with an item you've thrifted. The item you thrifted is:\n" \
        f"{new_item['title']}\n- {new_item['description']}\n- Category: {new_item['category']}\n- Style tags: {', '.join(new_item['style_tags'])}\n- Size: {new_item['size']}\n- Condition: {new_item['condition']}\n- Colors: {', '.join(new_item['colors'])}\n- Brand: {new_item['brand']}\n- Platform: {new_item['platform']}\n\n" \
        f"The outfit you have created is described here:\n{outfit}\n\n" \
        "Given this outfit and this thrifted item, write a casual and authentic 2-4 sentence caption for this OOTD that specifically captures the vibe of the outfit and naturally mentions the new item, its price, and platform."

    GROQ_CLIENT = _get_groq_client()

    response = GROQ_CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": PROMPT}
        ],
        temperature=0.5,
    )

    message = response.choices[0].message.content

    return message


if __name__ == "__main__":
    # # Quick manual test for search_listings
    # results = search_listings("graphic tee", size="L", max_price=35)
    # for r in results:
    #     # pretty print the results on one line with consistent separators and distance between fields
    #     print(f"{r['title'][:30]:30} | {r['size']:10} | ${r['price']:6.2f}")

    lsts = load_listings()
    item1 = lsts[0]
    item2 = lsts[1]

    style = suggest_outfit(wardrobe=get_example_wardrobe(), new_item=item1)
    style_empty = suggest_outfit(wardrobe=get_empty_wardrobe(), new_item=item2)

    print(create_fit_card(style, item1))
    print(create_fit_card(style_empty, item2))