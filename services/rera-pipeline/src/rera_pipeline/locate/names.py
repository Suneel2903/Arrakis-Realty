"""Project-name normalisation and fuzzy matching.

RERA names carry phase numbers and generic words ("Prestige Lakeside Habitat Phase II",
"Sai Residency Apartments"); OSM and geocoders usually carry the bare complex name.
Matching compares the distinctive tokens only.
"""

import re
import unicodedata
from difflib import SequenceMatcher

# Words that say what kind of building it is, not which one.
GENERIC = frozenset(
    """
    phase ph apartment apartments apts apt residency residences residence tower towers
    block blocks wing wings stage project flats flat the at by of and in bangalore bengaluru
    blr pvt ltd private limited llp
    """.split()
)
ROMAN = frozenset("i ii iii iv v vi vii viii ix x xi xii".split())

# Strip only numbering from names sent to geocoders; keep words OSM names usually include.
_QUERY_STRIP = re.compile(
    r"\b(phase|ph|block|wing|tower|stage)\s*[-:]?\s*([0-9]+|[ivx]+|[a-d])\b|\b(phase|ph)\b",
    re.IGNORECASE,
)

MATCH_THRESHOLD = 0.92


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def tokens(name: str) -> list[str]:
    """Distinctive lower-case tokens of a name, generic words and numbering removed."""
    s = _ascii(name or "").lower().replace("&", " and ")
    s = re.sub(r"['\u2019]s\b", "", s)  # possessive: "T.S.R'S" -> "tsr"
    raw = re.findall(r"[a-z0-9]+", s)
    out: list[str] = []
    letters: list[str] = []
    for t in raw:
        # "S R Suvarana" -> "sr suvarana"
        if len(t) == 1 and t.isalpha():
            letters.append(t)
            continue
        if letters:
            out.append("".join(letters))
            letters = []
        out.append(t)
    if letters:
        out.append("".join(letters))
    return [t for t in out if t not in GENERIC and t not in ROMAN and not t.isdigit()]


def key(name: str) -> str:
    return " ".join(tokens(name))


def query_name(name: str) -> str:
    """Project name for a geocoder query: drop phase/tower numbering, keep everything else."""
    s = _QUERY_STRIP.sub(" ", name or "")
    return re.sub(r"\s+", " ", s).strip(" ,-")


def is_distinctive(name_tokens: list[str], promoter_tokens: set[str]) -> bool:
    """Reject names too generic to match on their own ("Green", "Prestige")."""
    if not name_tokens:
        return False
    if len(name_tokens) == 1:
        t = name_tokens[0]
        return len(t) >= 6 and t not in promoter_tokens
    return len("".join(name_tokens)) >= 6


def score(project: str, candidate: str, promoter: str = "") -> float:
    """Similarity of two names, 0..1. 1.0 means the distinctive tokens are identical."""
    a, b = tokens(project), tokens(candidate)
    if not a or not b:
        return 0.0
    if a == b or sorted(a) == sorted(b):
        return 1.0
    # Brand left off one side: "Prestige Lakeside Habitat" vs "Lakeside Habitat".
    brand = set(tokens(promoter))
    a2 = [t for t in a if t not in brand]
    b2 = [t for t in b if t not in brand]
    if a2 and b2 and sorted(a2) == sorted(b2) and len("".join(a2)) >= 6:
        return 0.95
    return SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()


def promoter_overlap(promoter: str, text: str) -> bool:
    """True when a distinctive promoter token appears in the candidate's name or tags."""
    p = {t for t in tokens(promoter) if len(t) >= 3}
    return bool(p & set(tokens(text)))
