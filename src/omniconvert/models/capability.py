"""Typed capability definitions and conversion schemas."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class Capability:
    id: str
    display_name: str
    description: str
    input_categories: List[str]
    input_formats: List[str]
    output_category: str
    output_format: str
    engine: str
    operation: str
    lossy: bool = False
    requires_user_choice: bool = False
    settings_schema: Dict[str, Any] = field(default_factory=dict)
    optional_dependencies: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    validation_type: str = "existence_and_size"

    def matches_input(self, detected_format: str, category: str) -> bool:
        """Check if capability applies to given file format and category."""
        format_match = detected_format.lower() in [f.lower() for f in self.input_formats] or "*" in self.input_formats
        category_match = category.lower() in [c.lower() for c in self.input_categories] or "*" in self.input_categories
        return format_match or category_match
