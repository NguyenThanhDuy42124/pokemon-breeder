import re
from functools import lru_cache


@lru_cache(maxsize=4096)
def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
