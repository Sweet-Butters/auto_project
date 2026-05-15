"""YouTube Data API videoCategoryId mapping + helpers.

Source: YouTube Data API v3 videoCategoryId values used for regular user
uploads. Movie-only categories (30-44) and region-specific spill-overs are
excluded — they don't appear on user-uploaded videos.

Public API:
    YT_CATEGORY_MAP   {int: (en, ko)}  — full table
    UNKNOWN_EN, UNKNOWN_KO            — fallback labels
    KR_TRENDING_IDS  list[int]        — curated subset useful for KR
                                        trending crawls (excludes long-tail
                                        / low-signal categories)
    lookup(id)       → (en, ko)
    label(id, lang)  → str            — convenience wrapper
    all_ids()        → list[int]
"""
from __future__ import annotations

from typing import Iterable

YT_CATEGORY_MAP: dict[int, tuple[str, str]] = {
    1:  ("Film & Animation",      "영화/애니메이션"),
    2:  ("Autos & Vehicles",      "자동차"),
    10: ("Music",                 "음악"),
    15: ("Pets & Animals",        "반려동물/동물"),
    17: ("Sports",                "스포츠"),
    19: ("Travel & Events",       "여행/행사"),
    20: ("Gaming",                "게임"),
    22: ("People & Blogs",        "사람/블로그"),
    23: ("Comedy",                "코미디"),
    24: ("Entertainment",         "엔터테인먼트"),
    25: ("News & Politics",       "뉴스/정치"),
    26: ("Howto & Style",         "하우투/스타일"),
    27: ("Education",             "교육"),
    28: ("Science & Technology",  "과학/기술"),
    29: ("Nonprofits & Activism", "비영리/사회운동"),
}

UNKNOWN_EN = "Uncategorized"
UNKNOWN_KO = "기타"

# Subset useful for trending crawls in KR: high-volume, content-creator
# heavy categories. Skips Film/Autos/Pets/Travel/Nonprofits which are
# either low-volume or movie-spillover noise.
KR_TRENDING_IDS: list[int] = [10, 17, 20, 22, 23, 24, 25, 26, 27, 28]


def lookup(category_id: int | str | None) -> tuple[str, str]:
    """Return (english, korean) for a YouTube category id.

    Accepts ints, numeric strings, or None. Falls back to
    (UNKNOWN_EN, UNKNOWN_KO) for None, unknown ids, or non-numeric input.
    """
    if category_id is None:
        return (UNKNOWN_EN, UNKNOWN_KO)
    try:
        cid = int(category_id)
    except (TypeError, ValueError):
        return (UNKNOWN_EN, UNKNOWN_KO)
    return YT_CATEGORY_MAP.get(cid, (UNKNOWN_EN, UNKNOWN_KO))


def label(category_id: int | str | None, lang: str = "ko") -> str:
    """Return just one label. `lang` is 'ko' (default) or 'en'."""
    en, ko = lookup(category_id)
    return ko if lang == "ko" else en


def all_ids() -> list[int]:
    """Every known category id, sorted."""
    return sorted(YT_CATEGORY_MAP.keys())


def filter_known(category_ids: Iterable[int | str | None]) -> list[int]:
    """Keep only ids that resolve to a real category (drops None/unknown/non-numeric)."""
    out: list[int] = []
    for cid in category_ids:
        if cid is None:
            continue
        try:
            i = int(cid)
        except (TypeError, ValueError):
            continue
        if i in YT_CATEGORY_MAP:
            out.append(i)
    return out
