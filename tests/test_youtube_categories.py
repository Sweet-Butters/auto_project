"""Tests for auto_project.youtube.categories."""
from __future__ import annotations

import pytest

from auto_project.youtube import categories


def test_lookup_known_id_returns_labels():
    assert categories.lookup(10) == ("Music", "음악")
    assert categories.lookup(27) == ("Education", "교육")


def test_lookup_accepts_string_input():
    assert categories.lookup("10") == ("Music", "음악")


def test_lookup_unknown_returns_fallback():
    assert categories.lookup(999) == (categories.UNKNOWN_EN, categories.UNKNOWN_KO)
    assert categories.lookup(None) == (categories.UNKNOWN_EN, categories.UNKNOWN_KO)
    assert categories.lookup("not-a-number") == (categories.UNKNOWN_EN, categories.UNKNOWN_KO)


def test_label_picks_lang():
    assert categories.label(10) == "음악"
    assert categories.label(10, lang="ko") == "음악"
    assert categories.label(10, lang="en") == "Music"


def test_label_falls_back_for_unknown():
    assert categories.label(999) == categories.UNKNOWN_KO
    assert categories.label(999, lang="en") == categories.UNKNOWN_EN


def test_kr_trending_ids_are_all_in_main_map():
    """If someone removes an id from the main map, KR_TRENDING_IDS shouldn't
    silently point to nothing."""
    for cid in categories.KR_TRENDING_IDS:
        assert cid in categories.YT_CATEGORY_MAP, f"id {cid} missing from YT_CATEGORY_MAP"


def test_kr_trending_ids_skip_long_tail():
    """Sanity: the curated subset doesn't include the long-tail/spillover."""
    # Movies, autos, pets, travel, nonprofits are intentionally NOT in KR set
    for excluded in (1, 2, 15, 19, 29):
        assert excluded not in categories.KR_TRENDING_IDS


def test_all_ids_is_sorted_and_complete():
    ids = categories.all_ids()
    assert ids == sorted(ids)
    assert set(ids) == set(categories.YT_CATEGORY_MAP.keys())


def test_filter_known_drops_invalid():
    result = categories.filter_known([10, "27", None, "abc", 9999, 28])
    assert result == [10, 27, 28]
