"""Geography-native subreddit bias for Voices on_target_geography tagging."""

from __future__ import annotations


def _normalize_geo(geography: str | None) -> str:
    if not geography:
        return ""
    return " ".join(geography.lower().split()).strip()


# Known geography-native subreddit names (lowercase, no r/ prefix).
_GEO_SUBREDDITS: dict[str, frozenset[str]] = {
    "india": frozenset(
        {
            "india",
            "indiasocial",
            "indianstreetbets",
            "bangalore",
            "mumbai",
            "delhi",
            "hyderabad",
            "chennai",
            "kolkata",
            "developersindia",
        }
    ),
    "germany": frozenset({"germany", "berlin", "munich", "deutschland"}),
    "uk": frozenset({"unitedkingdom", "uk", "askuk", "london"}),
    "united kingdom": frozenset({"unitedkingdom", "uk", "askuk", "london"}),
    "usa": frozenset({"usa", "unitedstates", "asknyc", "sanfrancisco", "losangeles"}),
    "united states": frozenset({"usa", "unitedstates", "asknyc", "sanfrancisco", "losangeles"}),
    "canada": frozenset({"canada", "toronto", "vancouver", "ontario"}),
    "australia": frozenset({"australia", "sydney", "melbourne"}),
    "japan": frozenset({"japan", "tokyo"}),
    "brazil": frozenset({"brasil", "brazil", "saopaulo"}),
}


def is_subreddit_on_target_geography(
    subreddit: str,
    target_geography: str | None,
) -> bool:
    """Return True when subreddit is geography-native for the founder's market."""
    geo = _normalize_geo(target_geography)
    if not geo:
        return False
    subs = _GEO_SUBREDDITS.get(geo)
    if subs is None:
        # Partial match on keys (e.g. "India" already normalized to india)
        for key, names in _GEO_SUBREDDITS.items():
            if key in geo or geo in key:
                subs = names
                break
    if subs is None:
        return False
    return subreddit.lower() in subs


def build_subreddit_geography_map(
    subreddits: list[str],
    target_geography: str | None,
) -> dict[str, bool]:
    """Map each subreddit to on_target_geography for LLM extraction."""
    return {
        sub: is_subreddit_on_target_geography(sub, target_geography)
        for sub in subreddits
    }
