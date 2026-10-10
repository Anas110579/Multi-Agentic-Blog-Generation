from blogboard.graph.graph import graph


def test_graph_dry_run_needs_no_live_credentials_or_storage() -> None:
    result = graph.invoke(
        {"date": "2026-10-05", "dry_run": True, "domain": "ml"},
        config={"configurable": {"thread_id": "test-dry-run"}},
    )

    assert result["domain"] == "ml"
    assert result["topic"]
    assert result["content"]
    assert result["title"] == "Dry Run Generated Title"
    assert result["md_path"] == "r2://dry-run"
