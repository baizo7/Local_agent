from __future__ import annotations

from pathlib import Path

from baizo.core.indexer import LocalIndexer
from baizo.core.semantic import LocalSemanticEngine, cosine_similarity


def test_cosine_similarity() -> None:
    v1 = {"apple": 0.5, "banana": 0.5}
    v2 = {"apple": 0.5, "banana": 0.5}
    v3 = {"car": 1.0}

    assert math_close(cosine_similarity(v1, v2), 1.0)
    assert math_close(cosine_similarity(v1, v3), 0.0)


def math_close(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) < tol


def test_semantic_engine(tmp_path: Path) -> None:
    db_file = tmp_path / "semantic_test.db"
    indexer = LocalIndexer(db_path=db_file)

    # Populate files
    f1 = tmp_path / "ai_robotics.txt"
    f1.write_text("Autonomous humanoid robotics and reinforcement learning algorithms.")
    f2 = tmp_path / "cooking_recipe.txt"
    f2.write_text("Italian pasta recipe with tomato basil sauce and parmesan cheese.")

    indexer.index_directory(tmp_path, index_content=True)

    engine = LocalSemanticEngine(db_path=db_file)
    results = engine.search_semantic("humanoid robotics algorithms")
    assert len(results) >= 1
    top_res, top_score = results[0]
    assert "ai_robotics.txt" in top_res.path.name
    assert top_score > 0.1
