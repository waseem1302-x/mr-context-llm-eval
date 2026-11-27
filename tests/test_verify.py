"""Tests for verify.py: existence, spatial claims, UI clutter, schema."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mr_context.scene import load_scenes
from mr_context.ui_schema import UISchemaItem, parse_ui_schema
from mr_context.verify import check_spatial_claim, extract_mentioned_objects, score_run

SCENES = load_scenes(os.path.join(os.path.dirname(__file__), "..", "data", "scenes"))
BY_ID = {s.scene_id: s for s in SCENES}


def test_twelve_scenes_loaded():
    assert len(SCENES) == 12


def test_hallucinated_object_counts_as_hallucination():
    scene = BY_ID["scene_01_desk"]
    scores, _ = score_run(
        "The blue mug is near the notebook.", [], [], scene, True
    )
    assert "notebook" in scores.hallucinated_objects
    assert scores.groundedness == 0.5
    assert scores.hallucination_rate == 0.5


def test_all_present_objects_grounded():
    scene = BY_ID["scene_01_desk"]
    scores, _ = score_run(
        "The blue mug is near the laptop.", [], [], scene, True
    )
    assert scores.groundedness == 1.0
    assert scores.hallucinated_objects == []


def test_correct_denial_is_not_hallucination():
    scene = BY_ID["scene_03_desk"]
    scores, _ = score_run(
        "There is no blue mug in this scene.", [], [], scene, True
    )
    assert scores.hallucinated_objects == []
    assert scores.mentioned_total == 0


def test_wrong_near_far_claim_fails():
    scene = BY_ID["scene_02_desk"]
    # Mug is far (2.09 m) from laptop (0.60 m): euclidean distance is large.
    check = check_spatial_claim(
        {"subject": "blue mug", "relation": "near", "object": "laptop"}, scene
    )
    assert check.correct is False
    check2 = check_spatial_claim(
        {"subject": "blue mug", "relation": "far", "object": "laptop"}, scene
    )
    assert check2.correct is True


def test_left_right_claim():
    scene = BY_ID["scene_01_desk"]
    # laptop x -0.30 is left of blue mug x 0.10
    check = check_spatial_claim(
        {"subject": "laptop", "relation": "left", "object": "blue mug"}, scene
    )
    assert check.correct is True
    check2 = check_spatial_claim(
        {"subject": "laptop", "relation": "right", "object": "blue mug"}, scene
    )
    assert check2.correct is False


def test_claim_about_absent_object_fails():
    scene = BY_ID["scene_03_desk"]
    check = check_spatial_claim(
        {"subject": "blue mug", "relation": "near", "object": "laptop"}, scene
    )
    assert check.correct is False
    assert "not in scene" in check.reason


def test_ui_anchor_on_occluded_object_flagged():
    scene = BY_ID["scene_05_kitchen"]
    item = UISchemaItem(
        component="label", text="kettle", anchor_object="red kettle",
        depth_layer="near", priority=1,
    )
    scores, _ = score_run("The red kettle is occluded.", [], [item], scene, True)
    assert scores.ui_occluded_anchors == ["red kettle"]


def test_ui_anchor_on_absent_object_flagged():
    scene = BY_ID["scene_06_kitchen"]
    item = UISchemaItem(
        component="label", text="kettle", anchor_object="red kettle",
        depth_layer="near", priority=1,
    )
    scores, _ = score_run("There is no red kettle.", [], [item], scene, True)
    assert scores.ui_absent_anchors == ["red kettle"]


def test_invalid_schema_flagged():
    items, valid, errors = parse_ui_schema(
        [{"component": "label", "text": "x", "anchor_object": "mug",
          "depth_layer": "near", "priority": 9}]
    )
    assert valid is False
    assert errors


def test_synonym_maps_to_canonical():
    found = extract_mentioned_objects(
        "The slides are on the bench.", {"slides": "microscope slide box"}
    )
    assert "microscope slide box" in found


def test_spatial_accuracy_counts():
    scene = BY_ID["scene_01_desk"]
    scores, checks = score_run(
        "The blue mug is near the laptop.",
        [
            {"subject": "blue mug", "relation": "near", "object": "laptop"},
            {"subject": "blue mug", "relation": "far", "object": "laptop"},
        ],
        [],
        scene,
        True,
    )
    assert scores.spatial_total == 2
    assert scores.spatial_correct == 1
    assert scores.spatial_accuracy == 0.5
    assert len(checks) == 2
