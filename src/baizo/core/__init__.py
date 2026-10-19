from .content import ContentMatch, ContentSearcher
from .drives import get_available_roots
from .filters import SearchFilter, parse_date_filter, parse_size_to_bytes
from .indexer import LocalIndexer
from .parsers import (
    extract_document_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_xlsx,
)
from .search import SearchEngine, SearchResult, SearchStats
from .semantic import LocalSemanticEngine
from .watcher import start_watcher

__all__ = [
    "SearchResult",
    "SearchStats",
    "SearchEngine",
    "SearchFilter",
    "parse_size_to_bytes",
    "parse_date_filter",
    "get_available_roots",
    "ContentMatch",
    "ContentSearcher",
    "LocalIndexer",
    "extract_document_text",
    "extract_text_from_pdf",
    "extract_text_from_docx",
    "extract_text_from_xlsx",
    "extract_text_from_pptx",
    "LocalSemanticEngine",
    "start_watcher",
]
