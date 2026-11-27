"""Prompt builders: blind (query only) vs context-aware (query plus scene).

Lai rules, from Lai CHI 2026 (Searching Through Complex Worlds):
- Complex environments and varied virtual depth impair visual search.
- Depth cues can compensate for that impairment.
- Implicit memory for repeated spatial layouts stays robust under load.
So the context prompt tells the model to use depth as a grouping cue, keep
repeated layouts stable, and never place UI on occluded objects.
"""
from __future__ import annotations

import json
import math

from .scene import Scene, SceneObject

LAI_RULES = (
    "Lai rules (CHI 2026): use depth as a grouping cue; keep repeated "
    "spatial layouts stable; do not add a UI element for an occluded object; "
    "do not mention an object that is not in the scene."
)

SYSTEM_INSTRUCTION = (
    "You are a context-aware assistant for mixed reality. "
    "Answer only from the information given. "
    "Return JSON only, with keys: answer, spatial_claims, ui_schema. "
    "spatial_claims is a list of {subject, relation, object} where relation is "
    "one of: near, far, left, right, behind, in front of. "
    "ui_schema is a list of {component, text, anchor_object, depth_layer, priority} "
    "where component is one of: label, card, highlight, button."
)


def compute_spatial_relations(scene: Scene) -> list[dict]:
    """Pairwise relations computed in code, not by the LLM."""
    relations = []
    objs = scene.objects
    for i, a in enumerate(objs):
        for b in objs[i + 1:]:
            dist = round(
                math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2), 2
            )
            relations.append(
                {
                    "a": a.name,
                    "b": b.name,
                    "euclidean_m": dist,
                    "a_depth_layer": a.depth_layer,
                    "b_depth_layer": b.depth_layer,
                    "a_occluded": a.occluded,
                    "b_occluded": b.occluded,
                }
            )
    return relations


def build_blind_prompt(query: str) -> str:
    """Query only. No scene, no objects, no coordinates."""
    return (
        SYSTEM_INSTRUCTION
        + "\n\nUser query: "
        + query
        + "\n\nYou have no scene information. Answer from the query alone."
    )


def build_context_prompt(scene: Scene) -> str:
    """Query plus scene JSON plus code-computed spatial relations plus Lai rules."""
    scene_json = json.dumps(scene.model_dump(), indent=2)
    relations = json.dumps(compute_spatial_relations(scene), indent=2)
    visible = [o.name for o in scene.visible_objects()]
    occluded = [o.name for o in scene.objects if o.occluded]
    gaze = scene.gaze_object()
    return (
        SYSTEM_INSTRUCTION
        + "\n\n"
        + LAI_RULES
        + "\n\nScene JSON:\n"
        + scene_json
        + "\n\nSpatial relations computed from coordinates:\n"
        + relations
        + "\n\nVisible objects: "
        + ", ".join(visible)
        + "\nOccluded objects (do not show UI for these): "
        + (", ".join(occluded) if occluded else "none")
        + "\nGaze target: "
        + (gaze.name if gaze else "none")
        + "\n\nUser query: "
        + scene.user_query
    )


def target_object_name(query: str) -> str:
    """Best-effort target name from a query, used only by the mock backend."""
    lowered = query.lower()
    for name in (
        "blue mug",
        "red kettle",
        "microscope slide box",
        "laptop",
        "mug",
        "kettle",
        "slide box",
    ):
        if name in lowered:
            return name
    return "object"
