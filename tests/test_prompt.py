"""Tests for prompt builders and the VIGOR gate."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mr_context.llm import GATE_THRESHOLD, mock_generate, vigor_gate, vigor_scores
from mr_context.prompt import (
    LAI_RULES,
    build_blind_prompt,
    build_context_prompt,
    compute_spatial_relations,
)
from mr_context.scene import load_scenes

SCENES = load_scenes(os.path.join(os.path.dirname(__file__), "..", "data", "scenes"))
BY_ID = {s.scene_id: s for s in SCENES}


def test_blind_prompt_has_no_scene():
    prompt = build_blind_prompt("Where is the blue mug?")
    assert "blue mug" in prompt
    assert "Scene JSON" not in prompt
    assert '"objects"' not in prompt
    assert "0.35" not in prompt


def test_context_prompt_has_scene_and_lai_rules():
    scene = BY_ID["scene_01_desk"]
    prompt = build_context_prompt(scene)
    assert "Scene JSON" in prompt
    assert "blue mug" in prompt
    assert LAI_RULES[:40] in prompt
    assert "occluded" in prompt.lower()


def test_spatial_relations_computed_in_code():
    scene = BY_ID["scene_01_desk"]
    relations = compute_spatial_relations(scene)
    assert len(relations) == 10  # 5 objects, 5 choose 2
    assert all("euclidean_m" in r for r in relations)


def test_gate_present_visible_high_margin_no_recheck():
    scene = BY_ID["scene_01_desk"]
    decision = vigor_gate("blue mug", scene)
    assert decision.margin > GATE_THRESHOLD
    assert decision.recheck_triggered is False
    assert decision.kept is True


def test_gate_absent_low_margin_recheck_drops():
    scene = BY_ID["scene_03_desk"]
    decision = vigor_gate("blue mug", scene)
    assert decision.margin < GATE_THRESHOLD
    assert decision.recheck_triggered is True
    assert decision.recheck_result == "confirmed absent"
    assert decision.kept is False


def test_gate_occluded_low_margin_recheck_drops():
    scene = BY_ID["scene_05_kitchen"]
    decision = vigor_gate("red kettle", scene)
    assert decision.margin == 0.10
    assert decision.recheck_triggered is True
    assert decision.kept is False


def test_vigor_scores_are_deterministic_mock_not_logits():
    scene = BY_ID["scene_01_desk"]
    assert vigor_scores("blue mug", scene) == (0.92, 0.08)
    assert vigor_scores("notebook", scene) == (0.30, 0.70)


def test_mock_context_names_only_present_objects():
    scene = BY_ID["scene_01_desk"]
    out = mock_generate(scene, "context", scene.user_query)
    assert "blue mug" in out.answer
    assert "notebook" not in out.answer
    assert out.backend == "mock"


def test_mock_context_absent_target_says_so():
    scene = BY_ID["scene_03_desk"]
    out = mock_generate(scene, "context", scene.user_query)
    assert "no blue mug" in out.answer.lower()
    assert out.ui_schema == []


def test_mock_context_occluded_target_has_no_ui():
    scene = BY_ID["scene_05_kitchen"]
    out = mock_generate(scene, "context", scene.user_query)
    assert "occluded" in out.answer.lower()
    assert out.ui_schema == []


def test_mock_blind_mentions_prior_objects():
    scene = BY_ID["scene_01_desk"]
    out = mock_generate(scene, "blind", scene.user_query)
    assert "notebook" in out.answer
    assert out.gate_decisions == []
