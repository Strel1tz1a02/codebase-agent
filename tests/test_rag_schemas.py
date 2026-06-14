from src.rag.schemas import RagHit


def test_rag_hit_exports_graph_compatible_dict():
    hit = RagHit(
        relative_path="src/main.py",
        start_line=1,
        end_line=2,
        content="def main(): pass",
        score=0.5,
    )

    assert hit.to_dict() == {
        "relative_path": "src/main.py",
        "start_line": 1,
        "end_line": 2,
        "content": "def main(): pass",
        "score": 0.5,
    }
