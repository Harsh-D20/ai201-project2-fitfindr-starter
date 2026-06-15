# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tool Inventory

### Tool 1: search_listings

**What it does:**
This tool searches the listings for items matching the user's query request. 

**Input parameters:**
- `description` (str): a description of the item. Required Field.
- `size` (str): the size of the item requested. If not provided, will use any size that matches other criteria best.
- `max_price` (float): the max price of the item requested. If not provided, will use any price that matches other criteria best. 

**What it returns:**
The return value is a list of listings that match the user query, `matches` (list[dict]).

**What happens if it fails or returns nothing:**
If there are no listings that match, the agent will terminate the conversation and inform the user to try something else.

---

### Tool 2: suggest_outfit

**What it does:**
This tool takes the top item found from search results and the user's wardrobe (i.e. style) and returns how to style the item with their current items. 

**Input parameters:**
- `new_item` (dict): This is the top (first) listing from the `matches` returned by search_listings in step 1.
- `wardrobe` (dict): This represents the user's current clothing and their preferences. 

**What it returns:**
This should return a string describing the outfit that would work best with the item from what is currently available in the wardrobe.

**What happens if it fails or returns nothing:**
If no outfit can be suggested, the tool returns general styling advice for the item.

---

### Tool 3: create_fit_card

**What it does:**
This tool takes the outfit description and the top item being thrifted to create a short caption that can be used on Instagram/TikTok.

**Input parameters:**
- `outfit` (str): a string describing the outfit that would work best with the item listed
- `new_item` (dict): This is the top (first) listing from the `matches` returned by search_listings in step 1 (same item as Tool 2).

**What it returns:**
This tool returns a short string which can be used as a social media caption for the outfit.

**What happens if it fails or returns nothing:**
If the outfit is incomplete, the tool should return an error message describing what is missing. It should not error suddenly or silently.

---

## Planning Loop Explanation
The agent follows a strict sequential pipeline:
1. **Call search_listings()** with the user's query parameters (description, optional size, optional max_price)
2. **Check results**: If search_listings returns an empty list, terminate and tell the user no matches were found
3. **Extract top result**: If results exist, take the first item (index 0) from the matches list
4. **Call suggest_outfit()** with the top result and the user's wardrobe to get styling advice
5. **Call create_fit_card()** with the outfit description and top result to generate a social media caption
6. **Return final response** with the listing, outfit suggestion, and caption to the user

The agent does not loop or retry — it follows this path once per user query.

---

## State Management

**How does information from one tool get passed to the next?**
The agent maintains the following state throughout a single user session:
- **search_results** (list[dict]): The full list of listings returned from search_listings()
- **top_result** (dict): The first item from search_results, selected for styling (extracted before calling suggest_outfit)
- **wardrobe** (dict): The user's wardrobe preferences, extracted from the user's input message
- **outfit_description** (str): The styling suggestion returned from suggest_outfit() for the top_result
- **final_caption** (str): The social media caption returned from create_fit_card()

Each tool's output becomes direct input to the next tool:
- search_listings output → extract top_result → input to suggest_outfit
- suggest_outfit output (outfit_description) → input to create_fit_card along with top_result
- create_fit_card output → final_caption returned to user

State persists only within a single user query — each new query starts fresh.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Tells the user: "No listings match your request, try loosening your requirements or searching for something else." |
| suggest_outfit | Wardrobe is empty | Tells the user: "It seems your wardrobe is empty, so here is some general styling advice for your item: ..." |
| create_fit_card | Outfit input is missing or incomplete | Tells user: "A post caption for this outfit cannot be generated." |

---

## Spec Reflection

**One way the spec helped you during implementation:**
The spec helped in specifying the potential errors in the code, so Claude was able to specifically ensure that these errors were addressed.

**One way your implementation diverged from the spec, and why:**
Initially, I only wanted to search listings based on description, but I observed that some keywords got passed over if they were only present in the title. So I added the title and the description to the keywords to search when searching listings. 

## AI Usage
**Instance 1 — Extracting the top listings**

- *What I gave the AI:* I gave Claude the `tools.py`, `planning.md`, and `data/listings.json`. I then asked it to implement the search listings function. 
- *What it produced:* It produced a description-only search function that did not account for how shoe sizes, pants sizes, and top sizes differ, as well as any 'one size fits all' sizes. 
- *What I changed or overrode:* I manually went in and wrote some logic to fix the sizing filtering. This can be found in `tools.py` under `search_listing()` lines 93-98.

**Instance 2 — Returning the results of search listings**

- *What I gave the AI:* I gave Claude the `tools.py`, `planning.md`, and `data/listings.json`. I then asked it to implement the search listings function. I told it to handle ties as best appropriate. 
- *What it produced:* It produced code that would return the sorted listings by their score value, with a secondary sort by price.
- *What I changed or overrode:* I removed the secondary sort, so there was only sorting by score. This was because the results seemed to go out-of-spec.