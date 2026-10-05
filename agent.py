"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. Check session["error"] first — if it isn't None,
        the run ended early and the later fields will still be None.
    """
    # 1. Start a session
    session = new_session(query, wardrobe)

    # 2. Track iterations
    iterations = 0
    iterations += 1
    trace.check_iterations(iterations)

    # 3. Parse query constraints (Price and Size)
    words = query.lower().split()
    max_price = None
    for i, word in enumerate(words):
        if "$" in word:
            try:
                max_price = float(word.replace("$", "").replace(",", ""))
            except ValueError:
                pass
        elif word == "under" and i + 1 < len(words):
            next_word = words[i + 1].replace("$", "")
            try:
                max_price = float(next_word)
            except ValueError:
                pass

    size = None
    valid_sizes = ["XXS", "XS", "S", "M", "L", "XL", "XXL"]
    for word in words:
        if word.upper() in valid_sizes:
            size = word.upper()
            break

    # Clean description string
    description = query
    for remove_word in ["under", f"${max_price}" if max_price else "", "size", size if size else ""]:
        if remove_word:
            description = description.replace(str(remove_word), "")
    description = " ".join(description.split())

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # 4. Call Tool 1: search_listings
    results = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )
    session["search_results"] = results

    # ⚠️ BRANCH RULE: Check if search results are empty
    if not session["search_results"]:
        filters_applied = []
        if size:
            filters_applied.append(f"size '{size}'")
        if max_price:
            filters_applied.append(f"budget under ${max_price:.2f}")

        filter_str = " and ".join(filters_applied) if filters_applied else "your query parameters"
        session["error"] = (
            f"No listings found matching {filter_str}. "
            "Try broadening your search by raising your price limit, removing size constraints, or using simpler search terms."
        )
        return session

    # 5. Choose an item and place in session state
    session["selected_item"] = session["search_results"][0]

    # 6. Call Tool 2: suggest_outfit using session state
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=session["wardrobe"],
    )

    # 7. Call Tool 3: create_fit_card using session state
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )

    # 8. Return finished session
    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
