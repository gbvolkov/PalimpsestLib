from dataclasses import dataclass
from typing import Dict, Set
import hashlib

from postal.parser import parse_address
from postal.normalize import normalize_string
from postal.expand import expand_address

# Order matters: this defines your canonical layout
CANON_ORDER = [
    "house", "house_number", "road",
    "unit", "level", "entrance", "staircase",
    "suburb", "city_district", "city",
    "state_district", "state",
    "postcode",
    "country",
]

@dataclass
class UnifiedAddress:
    raw: str                     # original string
    parts: Dict[str, str]        # parsed components (raw from libpostal)
    norm_parts: Dict[str, str]   # normalized components
    canonical: str               # canonical string
    canonical_hash: str          # stable hash for exact lookup
    fuzzy_keys: Set[str]         # expand_address variants (for fuzzy matching)
    fuzzy_hash: str              # optional: hash of fuzzy_keys for clustering


def unify_address(raw: str) -> UnifiedAddress:
    # 1. pre-clean whitespace
    raw = " ".join(raw.strip().split())

    # 2. parse into components
    parts = dict(parse_address(raw))

    # 3. normalize each component
    norm_parts: Dict[str, str] = {}
    for value, label in parts.items():
        if not value:
            continue
        norm_parts[label] = value #normalize_string(value)

    # 4. build canonical string in fixed order
    canonical_parts = []
    for label in CANON_ORDER:
        if label in norm_parts:
            canonical_parts.append(f"{label}={norm_parts[label]}")
    canonical = "|".join(canonical_parts)

    # 5. hash canonical string (primary id)
    canonical_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # 6. fuzzy variants via expand_address (optional but useful)
    fuzzy_keys = set(expand_address(raw))  # can be large for some inputs

    # sort to get deterministic representation before hashing
    fuzzy_str = "\n".join(sorted(fuzzy_keys))
    fuzzy_hash = hashlib.sha256(fuzzy_str.encode("utf-8")).hexdigest()

    return UnifiedAddress(
        raw=raw,
        parts=parts,
        norm_parts=norm_parts,
        canonical=canonical,
        canonical_hash=canonical_hash,
        fuzzy_keys=fuzzy_keys,
        fuzzy_hash=fuzzy_hash,
    )
