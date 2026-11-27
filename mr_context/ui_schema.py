"""UI schema parser and validator. Invalid schema is a failure, never silently fixed."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

Component = Literal["label", "card", "highlight", "button"]
DepthLayer = Literal["near", "mid", "far"]


class UISchemaItem(BaseModel):
    component: Component
    text: str = Field(min_length=1)
    anchor_object: str = Field(min_length=1)
    depth_layer: DepthLayer
    priority: int = Field(ge=1, le=3)


def parse_ui_schema(raw: list) -> tuple[list[UISchemaItem], bool, list[str]]:
    """Parse a raw list into UISchemaItems. Returns items, valid flag, errors."""
    if not isinstance(raw, list):
        return [], False, ["ui_schema is not a list"]
    items: list[UISchemaItem] = []
    errors: list[str] = []
    for i, entry in enumerate(raw):
        try:
            items.append(UISchemaItem.model_validate(entry))
        except ValidationError as exc:
            errors.append(f"ui_schema[{i}]: {exc.errors()[0]['msg']}")
    if errors:
        return items, False, errors
    return items, True, []
