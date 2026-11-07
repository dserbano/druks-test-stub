"""Tag (taxonomy) collection."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-") or "untagged"


@dataclass
class TagIndex:
    tags: Dict[str, List] = field(default_factory=lambda: defaultdict(list))

    def add(self, page) -> None:
        for tag in getattr(page, "tags", None) or []:
            self.tags[tag].append(page)

    def collect(self, pages: Iterable) -> None:
        for p in pages:
            self.add(p)

    def sorted_names(self) -> List[str]:
        return sorted(self.tags.keys())
