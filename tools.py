"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.
    """
    listings = load_listings()
    scored_results = []

    # Tokenize target size into separate normalized size tokens (e.g. "S/M" -> {"S", "M"})
    target_size_tokens = set(size.upper().replace("/", " ").split()) if size else set()
    query_keywords = [kw.lower() for kw in description.split()] if description else []

    for item in listings:
        # 1. Price Filter (Inclusive)
        item_price = float(item.get("price", 0))
        if max_price is not None and item_price > float(max_price):
            continue

        # 2. Size Filter (Exact token match to prevent "s" matching "us 9" or "l" matching "xl")
        if target_size_tokens:
            item_size = str(item.get("size", "")).upper()
            item_size_tokens = set(item_size.replace("/", " ").split())
            if not target_size_tokens.intersection(item_size_tokens):
                continue

        # 3. Score keyword overlap across title, description, category, and style tags
        score = 0
        if query_keywords:
            text_corpus = (
                f"{item.get('title', '')} "
                f"{item.get('description', '')} "
                f"{item.get('category', '')} "
                f"{' '.join(item.get('style_tags', []))}"
            ).lower()

            for kw in query_keywords:
                if kw in text_corpus:
                    score += 1

            # Drop items with zero keyword overlap when a query was provided
            if score == 0:
                continue
        else:
            score = 1

        scored_results.append((score, item))

    # 4. Sort by score descending (best match first)
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # 5. Extract items up to SEARCH_RESULT_LIMIT
    limit = getattr(config, "SEARCH_RESULT_LIMIT", 5)
    return [item for _, item in scored_results[:limit]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.
    """
    if not new_item:
        return "No item provided to generate outfit recommendations."

    wardrobe_items = wardrobe.get("items", []) if wardrobe else []

    item_title = new_item.get("title", "Selected Item")
    item_desc = new_item.get("description", "")
    item_category = new_item.get("category", "")

    if not wardrobe_items:
        prompt = (
            f"I am considering buying this thrifted item: '{item_title}' ({item_category}). "
            f"Item details: {item_desc}.\n"
            "My current wardrobe is empty. Provide 2 to 3 general styling tips and creative outfit ideas "
            "for how to wear and pair this item with common wardrobe staples."
        )
    else:
        formatted_wardrobe = []
        for w_item in wardrobe_items:
            title = w_item.get("title", "Item")
            cat = w_item.get("category", "")
            color = ", ".join(w_item.get("colors", []))
            formatted_wardrobe.append(f"- {title} ({cat}, colors: {color})")

        wardrobe_str = "\n".join(formatted_wardrobe)
        prompt = (
            f"I am considering buying this thrifted item: '{item_title}' ({item_category}). "
            f"Item details: {item_desc}.\n\n"
            f"Here are the items in my existing wardrobe:\n{wardrobe_str}\n\n"
            "Suggest 1 or 2 specific outfit combinations combining the new thrifted item with specific pieces "
            "from my wardrobe. Name the specific wardrobe items used."
        )

    response = generate(prompt)
    return response.strip() if response else "Unable to generate outfit suggestions at this time."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.
    """
    if not new_item:
        return "Error: Cannot generate fit card without a valid item."

    if not outfit or not outfit.strip():
        return "No outfit suggestions available to generate a fit card caption."

    item_title = new_item.get("title", "Thrift Find")
    price = new_item.get("price", "N/A")
    platform = new_item.get("platform", "online marketplace")

    prompt = (
        f"Write an engaging social media post caption (2 to 4 sentences, strictly under 280 characters) "
        f"celebrating a new thrifting find.\n"
        f"Item: '{item_title}' listed for ${price} on {platform}.\n"
        f"Outfit ideas: {outfit}\n\n"
        f"Requirements:\n"
        f"1. Read like an authentic user post (not a product advertisement).\n"
        f"2. Explicitly mention the item title ('{item_title}'), its price (${price}), and the platform ({platform}).\n"
        f"3. Capture the overall style vibe and stay strictly under 280 characters."
    )

    caption = generate(prompt)
    return caption.strip() if caption else f"Check out this {item_title} I found for ${price} on {platform}!"