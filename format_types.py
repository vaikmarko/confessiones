"""
Format Types
============

Shared format type definitions to avoid circular imports.
"""

from enum import Enum

class FormatType(Enum):
    # Social Media Formats
    X = "x"  # X (formerly Twitter)
    LINKEDIN = "linkedin" 
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    
    # Creative Formats
    POEM = "poem"
    SONG = "song"
    REEL = "reel"
    FAIRYTALE = "fairytale"
    
    # Professional Formats
    ARTICLE = "article"
    BLOG_POST = "blog_post"
    PRESENTATION = "presentation"
    NEWSLETTER = "newsletter"
    PODCAST = "podcast"
    LETTER = "letter"
    
    # Therapeutic Formats
    REFLECTION = "reflection"
    INSIGHTS = "insights"
    GROWTH_SUMMARY = "growth_summary"
    JOURNAL_ENTRY = "journal_entry"
    
    # Compilation format
    BOOK_CHAPTER = "book_chapter"
