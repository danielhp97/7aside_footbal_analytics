"""Canonical player name aliases and OCR noise cleanup."""

import re

_ALIASES: dict[str, str] = {
    # Luis Zé variants (OCR and typing)
    "luis ze": "Luis Zé",
    "lufs zé": "Luis Zé",
    "lufs ze": "Luis Zé",
    "lufs": "Luis Zé",
    "luis zé": "Luis Zé",
    "luis": "Luis Zé",
    # Ambrosio (leading underscore OCR noise)
    "_ambrésio": "Ambrosio",
    "ambrésio": "Ambrosio",
    # Remora (heavy OCR garbling)
    "revoltevesvesvas": "Remora",
    # Aseugarb variants
    "aseubarg": "Aseugarb",
    # Bocesso variants
    "bucesso": "Bocesso",
    # Chupa variants
    "xupa": "Chupa",
    # Pés de Sapo capitalisation variants
    "pés de sapo": "Pés de Sapo",
    "pes de sapo": "Pés de Sapo",
}


def _strip_ocr_noise(name: str) -> str:
    """Remove leading/trailing OCR symbol artifacts (!, /, », >, <, [=], }, etc.)."""
    name = re.sub(r"^[\W_]+", "", name)   # leading non-word chars
    name = re.sub(r"[\s{}|_©]+$", "", name)  # trailing noise
    return name.strip()


_GARBAGE_RE = re.compile(
    r"keamk|\.com|http|©|\[™|avin|GiGa|COVe|mmnmwvt", re.IGNORECASE
)


def is_garbage(name: str) -> bool:
    """Return True if *name* looks like OCR footer/watermark noise."""
    if _GARBAGE_RE.search(name):
        return True
    alpha = sum(c.isalpha() for c in name)
    return len(name) > 20 and alpha < len(name) * 0.55


def canonical(name: str) -> str:
    """Strip OCR noise, then return the canonical player name."""
    name = _strip_ocr_noise(name)
    return _ALIASES.get(name.lower(), name)
