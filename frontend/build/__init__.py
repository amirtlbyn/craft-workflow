"""Build-tool inspection helpers."""

from .analyzer import (
    analyze_assets,
    analyze_bundle,
    analyze_performance,
    analyze_splitting,
    analyze_tree_shaking,
)
from .detection import BuildToolResult, detect

__all__ = [
    "BuildToolResult",
    "detect",
    "analyze_assets",
    "analyze_bundle",
    "analyze_performance",
    "analyze_splitting",
    "analyze_tree_shaking",
]
