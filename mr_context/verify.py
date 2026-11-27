"""Verification in code, not by LLM self-check.

Checks: object existence, spatial claims against x/y/z/distance, UI anchored
to occluded or absent objects, schema validity. Scores are computed here.
"""
from __future__ import annotations

import math
import re

from pydantic import BaseModel, Field

from .scene import Scene
from .ui_schema import UISchemaItem

# Canonical object vocabulary used to find mentions in answer text.
# Built from every object name in data/scenes plus the blind prior objects.
# Synonyms are applied before matching, see data/synonyms.json.
VOCABULARY = [
    "blue mug",
    "red kettle",
    "microscope slide box",
    "laptop",
    "mug",
    "kettle",
    "slide box",
    "microscope",
    "pipette rack",
    "test tube rack",
    "beaker",
    "centrifuge",
    "monitor",
    "keyboard",
    "desk plant",
    "desk lamp",
    "office chair",
    "stove",
    "cutting board",
    "fruit bowl",
    "cup",
    "pen holder",
    "book stack",
    "notebook",
    "phone",
]


def load_synonyms(path: str = "data/synonyms.json") -> dict[str, str]:
    import json
    import os

    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return dict(json.load(f))


def extract_mentioned_objects(answer: str, synonyms: dict[str, str] | None = None) -> list[str]:
    """Object names mentioned in answer text, longest match first, deduplicated."""
    text = answer.lower()
    if synonyms:
        for alias, canonical in synonyms.items():
            text = re.sub(r"\b" + re.escape(alias.lower()) + r"\b", canonical.lower(), text)
    found: list[str] = []
    for name in sorted(VOCABULARY, key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", text):
            # Skip a short name if a longer name containing it was already found.
            if any(name in longer for longer in found):
                continue
            found.append(name)
    # Remove short names that are part of a longer found name.
    cleaned = []
    for name in found:
        if any(name != other and name in other for other in found):
            continue
        cleaned.append(name)
    # A correct denial ("There is no blue mug") is not a hallucination:
    # the object is named to say it is absent, which is the right answer.
    denied = [
        name
        for name in cleaned
        if re.search(r"\bno\s+" + re.escape(name) + r"\b", text)
    ]
    return [name for name in cleaned if name not in denied]


class SpatialCheck(BaseModel):
    claim: dict
    correct: bool
    reason: str


class Scores(BaseModel):
    groundedness: float
    hallucination_rate: float
    spatial_accuracy: float
    spatial_total: int
    spatial_correct: int
    mentioned_total: int
    mentioned_present: int
    hallucinated_objects: list[str] = Field(default_factory=list)
    schema_valid: bool
    ui_element_count: int
    ui_depth_layers: int
    ui_occluded_anchors: list[str] = Field(default_factory=list)
    ui_absent_anchors: list[str] = Field(default_factory=list)
    ui_clutter_score: float


def check_spatial_claim(claim: dict, scene: Scene) -> SpatialCheck:
    subject = str(claim.get("subject", ""))
    relation = str(claim.get("relation", ""))
    obj_name = str(claim.get("object", ""))
    a = scene.by_name(subject)
    b = scene.by_name(obj_name)
    if a is None:
        return SpatialCheck(claim=claim, correct=False, reason=f"subject {subject} not in scene")
    if b is None:
        return SpatialCheck(claim=claim, correct=False, reason=f"object {obj_name} not in scene")
    dist = math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
    if relation == "near":
        ok = dist <= 0.8
        return SpatialCheck(claim=claim, correct=ok, reason=f"euclidean {dist:.2f} m, near needs <= 0.80 m")
    if relation == "far":
        ok = dist >= 1.0
        return SpatialCheck(claim=claim, correct=ok, reason=f"euclidean {dist:.2f} m, far needs >= 1.00 m")
    if relation == "left":
        ok = a.x < b.x - 0.05
        return SpatialCheck(claim=claim, correct=ok, reason=f"a.x {a.x} vs b.x {b.x}")
    if relation == "right":
        ok = a.x > b.x + 0.05
        return SpatialCheck(claim=claim, correct=ok, reason=f"a.x {a.x} vs b.x {b.x}")
    if relation == "behind":
        ok = a.z > b.z + 0.05
        return SpatialCheck(claim=claim, correct=ok, reason=f"a.z {a.z} vs b.z {b.z}")
    if relation == "in front of":
        ok = a.z < b.z - 0.05
        return SpatialCheck(claim=claim, correct=ok, reason=f"a.z {a.z} vs b.z {b.z}")
    return SpatialCheck(claim=claim, correct=False, reason=f"unknown relation {relation}")


def score_run(
    answer: str,
    spatial_claims: list[dict],
    ui_schema: list[UISchemaItem],
    scene: Scene,
    schema_valid: bool,
    synonyms: dict[str, str] | None = None,
) -> tuple[Scores, list[SpatialCheck]]:
    mentioned = extract_mentioned_objects(answer, synonyms)
    present = [m for m in mentioned if scene.by_name(m) is not None]
    hallucinated = [m for m in mentioned if scene.by_name(m) is None]
    groundedness = (len(present) / len(mentioned)) if mentioned else 1.0
    checks = [check_spatial_claim(c, scene) for c in spatial_claims]
    correct = sum(1 for c in checks if c.correct)
    spatial_accuracy = (correct / len(checks)) if checks else 1.0
    occluded_anchors = []
    absent_anchors = []
    layers = set()
    for item in ui_schema:
        layers.add(item.depth_layer)
        target = scene.by_name(item.anchor_object)
        if target is None:
            absent_anchors.append(item.anchor_object)
        elif target.occluded:
            occluded_anchors.append(item.anchor_object)
    # Clutter: more elements and more layers is busier. 1 element in 1 layer scores 0.
    clutter = round(max(0, len(ui_schema) - 1) * 0.25 + max(0, len(layers) - 1) * 0.25, 2)
    scores = Scores(
        groundedness=round(groundedness, 3),
        hallucination_rate=round(1.0 - groundedness, 3),
        spatial_accuracy=round(spatial_accuracy, 3),
        spatial_total=len(checks),
        spatial_correct=correct,
        mentioned_total=len(mentioned),
        mentioned_present=len(present),
        hallucinated_objects=hallucinated,
        schema_valid=schema_valid,
        ui_element_count=len(ui_schema),
        ui_depth_layers=len(layers),
        ui_occluded_anchors=occluded_anchors,
        ui_absent_anchors=absent_anchors,
        ui_clutter_score=clutter,
    )
    return scores, checks
