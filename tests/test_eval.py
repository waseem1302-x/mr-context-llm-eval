"""Tests for the eval runner and the FastAPI app."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from mr_context.app import app
from mr_context.eval import PAIRS, run_all
from mr_context.scene import load_scenes

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "scenes")
SCENES = load_scenes(DATA)


def test_domains_have_three_scenes_each():
    from collections import Counter

    counts = Counter(s.domain for s in SCENES)
    assert counts == {"desk": 3, "kitchen": 3, "lab bench": 3, "office": 3}


def test_at_least_four_pairs_share_query_and_differ_by_one_fact():
    assert len(PAIRS) >= 4
    by_id = {s.scene_id: s for s in SCENES}
    for a_id, b_id, change in PAIRS:
        a, b = by_id[a_id], by_id[b_id]
        assert a.user_query == b.user_query
        assert change
        assert a.scene_id != b.scene_id


def test_paired_scenes_differ_in_only_one_object_fact():
    by_id = {s.scene_id: s for s in SCENES}
    a = by_id["scene_01_desk"]
    b = by_id["scene_02_desk"]
    names_a = {o.name for o in a.objects}
    names_b = {o.name for o in b.objects}
    assert names_a == names_b
    mug_a = a.by_name("blue mug")
    mug_b = b.by_name("blue mug")
    assert mug_a is not None and mug_b is not None
    assert mug_a.depth_layer != mug_b.depth_layer


def test_eval_run_reports_all_twelve_scenes():
    result = run_all(DATA, "mock")
    assert result["summary"]["n_scenes"] == 12
    assert len(result["rows"]) == 12
    for row in result["rows"]:
        assert "blind" in row and "context" in row


def test_mock_context_beats_blind_on_groundedness():
    result = run_all(DATA, "mock")
    s = result["summary"]
    assert s["mean_groundedness_context"] > s["mean_groundedness_blind"]
    assert s["mean_hallucination_context"] < s["mean_hallucination_blind"]


def test_mock_context_answer_changes_across_pairs():
    result = run_all(DATA, "mock")
    s = result["summary"]
    assert s["pairs_checked"] == 8
    # 7 of 8 change. The one that does not is scene_10 vs scene_11: the swap
    # was desk plant for desk lamp, neither is the laptop nearest neighbour
    # (keyboard is), so the target answer correctly stays stable. That is
    # spatial-regularity stability, not insensitivity, and it is reported.
    assert s["pairs_context_answer_changed"] == 7
    assert s["pairs_blind_answer_changed"] == 0


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_evaluate_endpoint_context():
    client = TestClient(app)
    scene = SCENES[0]
    resp = client.post(
        "/evaluate",
        json={"scene": scene.model_dump(), "mode": "context", "backend": "mock"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"] == "scene_01_desk"
    assert body["scores"]["groundedness"] == 1.0
    assert body["schema_valid"] is True


def test_evaluate_endpoint_blind_hallucinates():
    client = TestClient(app)
    scene = SCENES[0]
    resp = client.post(
        "/evaluate",
        json={"scene": scene.model_dump(), "mode": "blind", "backend": "mock"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scores"]["hallucination_rate"] > 0


def test_evaluate_endpoint_rejects_bad_mode():
    client = TestClient(app)
    scene = SCENES[0]
    resp = client.post(
        "/evaluate",
        json={"scene": scene.model_dump(), "mode": "wrong", "backend": "mock"},
    )
    assert resp.status_code == 400


def test_scenes_endpoint_lists_twelve():
    client = TestClient(app)
    resp = client.get("/scenes")
    assert resp.status_code == 200
    assert len(resp.json()["scenes"]) == 12
