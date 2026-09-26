"""Compatibility adapter around the RecoverAI Core package."""

from recoverai_core.analyzer import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    analyze_file,
)

__all__ = ["IMAGE_EXTENSIONS", "SUPPORTED_EXTENSIONS", "analyze_file"]
