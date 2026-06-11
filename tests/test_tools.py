# tests/test_tools.py
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)



LISTING = search_listings("vintage graphic tee", size=None, max_price=50)[0]

def test_no_wardrobe():
    result = suggest_outfit(new_item=LISTING, wardrobe=get_empty_wardrobe())
    assert isinstance(result, str)

def test_no_outfit():
    result = create_fit_card(new_item=LISTING, outfit="")
    assert isinstance(result, str)