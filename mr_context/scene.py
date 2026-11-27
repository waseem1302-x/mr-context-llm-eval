"""Pydantic models for MR scenes.

A scene is a synthetic JSON description of a physical space: objects with
x, y, z coordinates in metres, a distance from the user, a depth layer, and
flags for occlusion and gaze. No real photos, no headset captures.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DepthLayer = Literal["near", "mid", "far"]
Domain = Literal["desk", "kitchen", "lab bench", "office"]


def depth_layer_for_distance(distance_m: float) -> DepthLayer:
    if distance_m < 0.8:
        return "near"
    if distance_m <= 1.6:
        return "mid"
    return "far"


class SceneObject(BaseModel):
    name: str
    x: float
    y: float
    z: float
    distance_m: float = Field(gt=0)
    depth_layer: DepthLayer
    occluded: bool = False
    gaze_target: bool = False

    @model_validator(mode="after")
    def check_distance_and_layer(self) -> "SceneObject":
        expected = round(math.sqrt(self.x**2 + self.y**2 + self.z**2), 2)
        if abs(expected - self.distance_m) > 0.05:
            raise ValueError(
                f"distance_m {self.distance_m} does not match coordinates "
                f"(expected about {expected}) for object {self.name}"
            )
        if depth_layer_for_distance(self.distance_m) != self.depth_layer:
            raise ValueError(
                f"depth_layer {self.depth_layer} does not match distance_m "
                f"{self.distance_m} for object {self.name}"
            )
        return self


class Scene(BaseModel):
    scene_id: str
    domain: Domain
    task: str
    objects: list[SceneObject] = Field(min_length=3)
    user_query: str
    conversation_history: list[str] = Field(default_factory=list)
    paired_with: str | None = None
    paired_change: str | None = None

    def by_name(self, name: str) -> SceneObject | None:
        wanted = name.strip().lower()
        for obj in self.objects:
            if obj.name.lower() == wanted:
                return obj
        return None

    def visible_objects(self) -> list[SceneObject]:
        return [o for o in self.objects if not o.occluded]

    def gaze_object(self) -> SceneObject | None:
        for obj in self.objects:
            if obj.gaze_target:
                return obj
        return None


def load_scene(path: str) -> Scene:
    import json

    with open(path, encoding="utf-8") as f:
        return Scene.model_validate(json.load(f))


def load_scenes(directory: str) -> list[Scene]:
    import glob
    import os

    paths = sorted(glob.glob(os.path.join(directory, "scene_*.json")))
    return [load_scene(p) for p in paths]
