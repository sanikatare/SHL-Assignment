"""Data models for catalog management."""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
import json


@dataclass
class AssessmentItem:
    """Assessment item with all relevant metadata."""
    name: str
    url: str
    description: str
    category: str
    assessment_type: str
    test_type: str = ""  # Raw SHL test-type letter code(s), e.g. "K", "P", "A B"
    skills_measured: List[str] = field(default_factory=list)
    duration: str = ""
    remote_testing_support: bool = True
    adaptive_irt_support: bool = False
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssessmentItem":
        """Create instance from dictionary."""
        return cls(**data)
    
    def get_all_text(self) -> str:
        """Get concatenated text for TF-IDF vectorization."""
        parts = [
            self.name,
            self.description,
            self.category,
            self.assessment_type,
            " ".join(self.skills_measured),
            " ".join(self.keywords)
        ]
        return " ".join(parts).lower()


class CatalogManager:
    """Manage catalog operations."""
    
    def __init__(self, items: List[AssessmentItem] = None):
        self.items = items or []
    
    def add_item(self, item: AssessmentItem) -> None:
        """Add assessment item to catalog."""
        self.items.append(item)
    
    def remove_duplicate_urls(self) -> None:
        """Remove items with duplicate URLs, keeping first occurrence."""
        seen_urls = set()
        unique_items = []
        for item in self.items:
            if item.url not in seen_urls:
                unique_items.append(item)
                seen_urls.add(item.url)
        self.items = unique_items
    
    def to_json(self) -> str:
        """Convert catalog to JSON string."""
        data = [item.to_dict() for item in self.items]
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "CatalogManager":
        """Create catalog from JSON string."""
        data = json.loads(json_str)
        items = [AssessmentItem.from_dict(item) for item in data]
        return cls(items)
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries."""
        return [item.to_dict() for item in self.items]
    
    def get_by_url(self, url: str) -> AssessmentItem:
        """Get assessment by URL."""
        for item in self.items:
            if item.url == url:
                return item
        return None
    
    def get_by_name(self, name: str) -> List[AssessmentItem]:
        """Get assessments by name (partial match)."""
        name_lower = name.lower()
        return [item for item in self.items if name_lower in item.name.lower()]
    
    def size(self) -> int:
        """Get number of items in catalog."""
        return len(self.items)
    
    def search(self, query: str) -> List[AssessmentItem]:
        """Search catalog by query."""
        query_lower = query.lower()
        results = []
        for item in self.items:
            if query_lower in item.get_all_text():
                results.append(item)
        return results
