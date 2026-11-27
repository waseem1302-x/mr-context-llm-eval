"""Eval runner: run all 12 scenes blind and context-aware, write results.

No cherry-picking: every scene is reported, blind and context-aware side by
side, with the exact model, backend, date, and n.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os

from .llm import generate
from .scene import load_scenes
from .verify import load_synonyms, score_run

PAIRS = [
    ("scene_01_desk", "scene_02_desk", "blue mug moved near to far"),
    ("scene_01_desk", "scene_03_desk", "blue mug removed"),
    ("scene_04_kitchen", "scene_05_kitchen", "red kettle occluded"),
    ("scene_04_kitchen", "scene_06_kitchen", "red kettle removed"),
    ("scene_07_lab", "scene_08_lab", "pipette rack swapped for test tube rack"),
    ("scene_07_lab", "scene_09_lab", "gaze target changed"),
    ("scene_10_office", "scene_11_office", "desk plant swapped for desk lamp"),
    ("scene_10_office", "scene_12_office", "gaze target changed"),
]


def run_all(data_dir: str, backend: str = "mock") -> dict:
    scenes = load_scenes(data_dir)
    synonyms = load_synonyms(os.path.join(data_dir, "synonyms.json"))
    rows = []
    for scene in scenes:
        entry: dict = {"scene_id": scene.scene_id, "domain": scene.domain, "query": scene.user_query}
        for mode in ("blind", "context"):
            out = generate(scene, mode, backend)
            scores, checks = score_run(
                out.answer, out.spatial_claims, out.ui_schema, scene, out.schema_valid, synonyms
            )
            entry[mode] = {
                "answer": out.answer,
                "spatial_claims": out.spatial_claims,
                "spatial_checks": [c.model_dump() for c in checks],
                "ui_schema": [i.model_dump() for i in out.ui_schema],
                "gate_decisions": [g.model_dump() for g in out.gate_decisions],
                "scores": scores.model_dump(),
                "backend": out.backend,
                "model": out.model,
            }
        # Paired sensitivity is computed per pair below, not per row.
        rows.append(entry)
    by_id = {r["scene_id"]: r for r in rows}
    pairs = []
    for a_id, b_id, change in PAIRS:
        a = by_id.get(a_id)
        b = by_id.get(b_id)
        if a is None or b is None:
            continue
        pairs.append(
            {
                "a": a_id,
                "b": b_id,
                "change": change,
                "context_answer_changed": a["context"]["answer"] != b["context"]["answer"],
                "blind_answer_changed": a["blind"]["answer"] != b["blind"]["answer"],
            }
        )
    blind_grounded = [r["blind"]["scores"]["groundedness"] for r in rows]
    ctx_grounded = [r["context"]["scores"]["groundedness"] for r in rows]
    blind_hall = [r["blind"]["scores"]["hallucination_rate"] for r in rows]
    ctx_hall = [r["context"]["scores"]["hallucination_rate"] for r in rows]
    summary = {
        "n_scenes": len(rows),
        "backend": backend,
        "model": rows[0]["context"]["model"] if rows else "unknown",
        "date": datetime.date.today().isoformat(),
        "mean_groundedness_blind": round(sum(blind_grounded) / len(blind_grounded), 3) if rows else 0,
        "mean_groundedness_context": round(sum(ctx_grounded) / len(ctx_grounded), 3) if rows else 0,
        "mean_hallucination_blind": round(sum(blind_hall) / len(blind_hall), 3) if rows else 0,
        "mean_hallucination_context": round(sum(ctx_hall) / len(ctx_hall), 3) if rows else 0,
        "pairs_checked": len(pairs),
        "pairs_context_answer_changed": sum(1 for p in pairs if p["context_answer_changed"]),
        "pairs_blind_answer_changed": sum(1 for p in pairs if p["blind_answer_changed"]),
    }
    return {"summary": summary, "pairs": pairs, "rows": rows}


def write_results(result: dict, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    lines = []
    lines.append("# mr-context-llm-eval results")
    lines.append("")
    s = result["summary"]
    lines.append(f"Backend: {s['backend']}, model: {s['model']}, date: {s['date']}, n: {s['n_scenes']} scenes")
    lines.append("")
    lines.append(f"Mean groundedness blind: {s['mean_groundedness_blind']}, context: {s['mean_groundedness_context']}")
    lines.append(f"Mean hallucination blind: {s['mean_hallucination_blind']}, context: {s['mean_hallucination_context']}")
    lines.append(f"Paired scenes: {s['pairs_checked']}, context answer changed in {s['pairs_context_answer_changed']}, blind answer changed in {s['pairs_blind_answer_changed']}")
    lines.append("")
    lines.append("Mock note: the mock backend is a deterministic stand-in. Blind mode gets no scene, context mode gets the scene, so the mock delta is a property of that construction, not evidence about a real LLM. A live run is needed to measure a real delta.")
    lines.append("")
    lines.append("| scene | domain | grounded blind | grounded context | halluc blind | halluc context | spatial blind | spatial context | schema context |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in result["rows"]:
        b = r["blind"]["scores"]
        c = r["context"]["scores"]
        lines.append(
            f"| {r['scene_id']} | {r['domain']} | {b['groundedness']} | {c['groundedness']} | "
            f"{b['hallucination_rate']} | {c['hallucination_rate']} | {b['spatial_accuracy']} | "
            f"{c['spatial_accuracy']} | {c['schema_valid']} |"
        )
    lines.append("")
    lines.append("## Paired scenes")
    lines.append("")
    for p in result["pairs"]:
        lines.append(
            f"- {p['a']} vs {p['b']} ({p['change']}): context answer changed: {p['context_answer_changed']}, blind answer changed: {p['blind_answer_changed']}"
        )
    lines.append("")
    lines.append("## All answers (no cherry-picking)")
    lines.append("")
    for r in result["rows"]:
        lines.append(f"### {r['scene_id']} ({r['domain']})")
        lines.append(f"Query: {r['query']}")
        lines.append(f"Blind: {r['blind']['answer']}")
        lines.append(f"Context: {r['context']['answer']}")
        lines.append("")
    with open(os.path.join(out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="mock", choices=["mock", "live"])
    parser.add_argument("--data", default="data/scenes")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    result = run_all(args.data, args.mode)
    write_results(result, args.out)
    s = result["summary"]
    print(f"scenes: {s['n_scenes']}, backend: {s['backend']}, model: {s['model']}")
    print(f"mean groundedness blind {s['mean_groundedness_blind']} context {s['mean_groundedness_context']}")
    print(f"mean hallucination blind {s['mean_hallucination_blind']} context {s['mean_hallucination_context']}")
    print(f"pairs context changed {s['pairs_context_answer_changed']}/{s['pairs_checked']}")


if __name__ == "__main__":
    main()
