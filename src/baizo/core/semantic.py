from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .indexer import get_default_db_path
from .parsers import extract_document_text
from .search import SearchResult


def cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse term vectors."""
    intersection = set(v1.keys()) & set(v2.keys())
    if not intersection:
        return 0.0
    dot_product = sum(v1[k] * v2[k] for k in intersection)
    norm1 = math.sqrt(sum(val * val for val in v1.values()))
    norm2 = math.sqrt(sum(val * val for val in v2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot_product / (norm1 * norm2)


class LocalSemanticEngine:
    """Hybrid semantic search engine supporting Ollama dense embeddings with fast local TF-IDF fallback."""

    def __init__(self, ollama_url: Optional[str] = None, db_path: Optional[Path] = None) -> None:
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_API_URL") or "http://localhost:11434"
        self.db_path = db_path or get_default_db_path()
        self._init_semantic_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_semantic_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_docs (
                    path TEXT PRIMARY KEY,
                    filename TEXT,
                    tfidf_vector TEXT,
                    embedding_vector TEXT,
                    updated_at REAL
                )
                """
            )
            conn.commit()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was",
            "were", "will", "would", "can", "could", "should", "not", "have",
        }
        return [w for w in words if w not in stopwords]

    def _compute_tf_vector(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = float(len(tokens))
        return {term: count / total for term, count in counts.items()}

    def get_ollama_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        """Attempt to fetch dense vector embedding from local Ollama instance if active."""
        try:
            req_data = json.dumps({"model": model, "prompt": text[:2000]}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_url.rstrip('/')}/api/embeddings",
                data=req_data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("embedding")
        except Exception:
            return None

    def search_semantic(self, query: str, limit: int = 10) -> List[Tuple[SearchResult, float]]:
        """Search documents by semantic relevance score."""
        query_vector = self._compute_tf_vector(query)
        if not query_vector:
            return []

        results: List[Tuple[SearchResult, float]] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch content and vectors
            cursor.execute(
                """
                SELECT f.path, f.filename, f.is_dir, f.size, f.mtime, fts.content
                FROM files f
                LEFT JOIN fts_files fts ON f.path = fts.path
                WHERE f.is_dir = 0
                LIMIT 500
                """
            )
            rows = cursor.fetchall()

            for r in rows:
                content = r["content"] or ""
                doc_vector = self._compute_tf_vector(f"{r['filename']} {content}")
                sim = cosine_similarity(query_vector, doc_vector)
                if sim > 0.05:
                    res = SearchResult(
                        path=Path(r["path"]),
                        is_dir=bool(r["is_dir"]),
                        size=r["size"],
                        mtime=r["mtime"],
                        snippet=f"Relevance: {sim:.2f}",
                    )
                    results.append((res, sim))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:limit]
