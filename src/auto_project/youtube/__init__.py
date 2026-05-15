"""YouTube helpers shared across consumer projects.

Currently exports the official Data API category mapping. Project repos
that work with YouTube content (note-takers, trend crawlers, etc.) should
import from here rather than redefining their own mappings.
"""
from auto_project.youtube import categories

__all__ = ["categories"]
