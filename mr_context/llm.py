"""LLM layer: deterministic mock backend for CI, plus a live OpenAI-compatible backend.

The mock backend is a controlled stand-in, not a real model. It exists so the
verification pipeline can be tested without a key and without a headset.
Blind mode gets no scene, so it guesses from the query and a generic prior.
Context mode gets the scene, so it answers only from present, visible objects.
Any blind vs context delta in mock results is therefore a property of the
mock construction, not evidence about a real LLM. The live backend is the
place where a real delta would be measured.

VIGOR gate (deterministic mock analogue, NOT real MLLM logits, NOT VIGOR
paper code - no VIGOR code was found): for each candidate object, a yes/no
score pair is assigned by a fixed rule from scene state, margin
m = z_yes - z_no. Margin below the threshold triggers a re-check, which is a
second lookup of the scene JSON in code. The object is kept only if the
re-check confirms it is present and visible.
"""
from __future__ import annotations

import json
import math
import os

from pydantic import BaseModel, Field

from .prompt import build_blind_prompt, build_context_prompt, target_object_name
from .scene import Scene
from .ui_schema import UISchemaItem, parse_ui_schema

GATE_THRESHOLD = 0.30

# Generic prior objects the blind mock mentions. None of them appear in any
# scene in data/scenes, so blind mentions of them are hallucinations by
# construction. This is documented in the README.
BLIND_PRIOR_OBJECTS = ["notebook", "phone"]


class GateDecision(BaseModel):
    object: str
    z_yes: float
    z_no: float
    margin: float
    recheck_triggered: bool
    recheck_result: str
    kept: bool


class GeneratedOutput(BaseModel):
    answer: str
    spatial_claims: list[dict] = Field(default_factory=list)
    ui_schema: list[UISchemaItem] = Field(default_factory=list)
    gate_decisions: list[GateDecision] = Field(default_factory=list)
    backend: str
    model: str
    schema_valid: bool = True
    schema_errors: list[str] = Field(default_factory=list)


def vigor_scores(obj_name: str, scene: Scene) -> tuple[float, float]:
    """Deterministic yes/no scores from scene state. Mock analogue only."""
    obj = scene.by_name(obj_name)
    if obj is None:
        return 0.30, 0.70
    if obj.occluded:
        return 0.55, 0.45
    return 0.92, 0.08


def vigor_gate(obj_name: str, scene: Scene) -> GateDecision:
    z_yes, z_no = vigor_scores(obj_name, scene)
    margin = round(z_yes - z_no, 2)
    triggered = margin < GATE_THRESHOLD
    obj = scene.by_name(obj_name)
    if not triggered:
        return GateDecision(
            object=obj_name,
            z_yes=z_yes,
            z_no=z_no,
            margin=margin,
            recheck_triggered=False,
            recheck_result="not needed, margin above threshold",
            kept=True,
        )
    if obj is None:
        return GateDecision(
            object=obj_name,
            z_yes=z_yes,
            z_no=z_no,
            margin=margin,
            recheck_triggered=True,
            recheck_result="confirmed absent",
            kept=False,
        )
    if obj.occluded:
        return GateDecision(
            object=obj_name,
            z_yes=z_yes,
            z_no=z_no,
            margin=margin,
            recheck_triggered=True,
            recheck_result="confirmed occluded",
            kept=False,
        )
    return GateDecision(
        object=obj_name,
        z_yes=z_yes,
        z_no=z_no,
        margin=margin,
        recheck_triggered=True,
        recheck_result="confirmed present and visible",
        kept=True,
    )


def _nearest_visible(scene: Scene, target: str) -> tuple[str, str] | None:
    """Closest visible object to the target, with a near/far relation word."""
    tgt = scene.by_name(target)
    if tgt is None:
        return None
    best = None
    best_dist = None
    for obj in scene.visible_objects():
        if obj.name == tgt.name:
            continue
        dist = math.sqrt(
            (tgt.x - obj.x) ** 2 + (tgt.y - obj.y) ** 2 + (tgt.z - obj.z) ** 2
        )
        if best_dist is None or dist < best_dist:
            best, best_dist = obj, dist
    if best is None or best_dist is None:
        return None
    relation = "near" if best_dist <= 0.8 else "far"
    return best.name, relation


def mock_generate(scene: Scene | None, mode: str, query: str) -> GeneratedOutput:
    """Deterministic mock. Blind mode receives no scene at all."""
    if mode == "blind":
        target = target_object_name(query)
        answer = (
            f"The {target} is near the notebook and the phone. "
            f"The {target} is on the left side, near the notebook."
        )
        claims = [
            {"subject": target, "relation": "near", "object": "notebook"},
            {"subject": target, "relation": "left", "object": "notebook"},
        ]
        raw_schema = [
            {
                "component": "label",
                "text": f"{target} here",
                "anchor_object": target,
                "depth_layer": "near",
                "priority": 1,
            }
        ]
        items, valid, errors = parse_ui_schema(raw_schema)
        return GeneratedOutput(
            answer=answer,
            spatial_claims=claims,
            ui_schema=items,
            gate_decisions=[],
            backend="mock",
            model="mock-deterministic-v1",
            schema_valid=valid,
            schema_errors=errors,
        )

    if scene is None:
        raise ValueError("context mode requires a scene")
    target = target_object_name(query)
    # Resolve the target to the full canonical object name in the scene.
    canonical = None
    for obj in scene.objects:
        if target in obj.name.lower() or obj.name.lower() in target:
            canonical = obj.name
            break
    if canonical is None:
        canonical = target

    decisions = [vigor_gate(o.name, scene) for o in scene.objects]
    kept_names = {d.object for d in decisions if d.kept}

    tgt_obj = scene.by_name(canonical)
    if tgt_obj is None or not tgt_obj.occluded and canonical not in kept_names:
        # Target absent: say so, do not invent it.
        answer = (
            f"There is no {canonical} in this scene. "
            "I cannot point to it, and no UI element is shown for it."
        )
        return GeneratedOutput(
            answer=answer,
            spatial_claims=[],
            ui_schema=[],
            gate_decisions=decisions,
            backend="mock",
            model="mock-deterministic-v1",
            schema_valid=True,
            schema_errors=[],
        )
    if tgt_obj.occluded:
        answer = (
            f"The {canonical} is in this scene but it is occluded, "
            "so it is not shown in the UI. I will not place a label on it."
        )
        return GeneratedOutput(
            answer=answer,
            spatial_claims=[],
            ui_schema=[],
            gate_decisions=decisions,
            backend="mock",
            model="mock-deterministic-v1",
            schema_valid=True,
            schema_errors=[],
        )

    nearest = _nearest_visible(scene, canonical)
    gaze = scene.gaze_object()
    gaze_note = ""
    if gaze is not None and gaze.name != canonical:
        gaze_note = f" You are looking at the {gaze.name}."
    if nearest is None:
        answer = f"The {canonical} is in this scene, in the {tgt_obj.depth_layer} layer." + gaze_note
        claims: list[dict] = []
    else:
        neighbour, relation = nearest
        relation_phrase = "near the" if relation == "near" else "far from the"
        answer = (
            f"The {canonical} is {relation_phrase} {neighbour}, "
            f"in the {tgt_obj.depth_layer} depth layer. "
            f"The {neighbour} is the closest visible object to it."
            + gaze_note
        )
        claims = [
            {"subject": canonical, "relation": relation, "object": neighbour}
        ]
    raw_schema = [
        {
            "component": "label",
            "text": f"{canonical} ({tgt_obj.depth_layer})",
            "anchor_object": canonical,
            "depth_layer": tgt_obj.depth_layer,
            "priority": 1,
        }
    ]
    items, valid, errors = parse_ui_schema(raw_schema)
    return GeneratedOutput(
        answer=answer,
        spatial_claims=claims,
        ui_schema=items,
        gate_decisions=decisions,
        backend="mock",
        model="mock-deterministic-v1",
        schema_valid=valid,
        schema_errors=errors,
    )


def live_generate(scene: Scene | None, mode: str, query: str) -> GeneratedOutput:
    """Live OpenAI-compatible backend. Key from environment only, never hardcoded."""
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in the environment to use the live backend."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("MR_LLM_MODEL", "gpt-4o-mini")
    if mode == "blind":
        prompt = build_blind_prompt(query)
    else:
        if scene is None:
            raise ValueError("context mode requires a scene")
        prompt = build_context_prompt(scene)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
        answer = str(parsed.get("answer", ""))
        claims = list(parsed.get("spatial_claims", []))
        raw_schema = list(parsed.get("ui_schema", []))
    except (json.JSONDecodeError, AttributeError):
        return GeneratedOutput(
            answer=content,
            spatial_claims=[],
            ui_schema=[],
            gate_decisions=[],
            backend="live",
            model=model,
            schema_valid=False,
            schema_errors=["live output was not valid JSON with answer, spatial_claims, ui_schema"],
        )
    items, valid, errors = parse_ui_schema(raw_schema)
    decisions = []
    if scene is not None:
        seen: set[str] = set()
        for claim in claims:
            for key in ("subject", "object"):
                name = str(claim.get(key, ""))
                if name and name not in seen:
                    seen.add(name)
                    decisions.append(vigor_gate(name, scene))
    return GeneratedOutput(
        answer=answer,
        spatial_claims=claims,
        ui_schema=items,
        gate_decisions=decisions,
        backend="live",
        model=model,
        schema_valid=valid,
        schema_errors=errors,
    )


def generate(scene: Scene | None, mode: str, backend: str = "mock") -> GeneratedOutput:
    """One interface for both backends. mode is blind or context."""
    if mode not in ("blind", "context"):
        raise ValueError("mode must be blind or context")
    query = scene.user_query if scene is not None else ""
    if backend == "mock":
        return mock_generate(scene, mode, query)
    if backend == "live":
        return live_generate(scene, mode, query)
    raise ValueError("backend must be mock or live")
