# mr-context-llm-eval

A headset-free Python harness for testing context-aware LLM answers in mixed reality scenes. Scene JSON in, context-aware LLM answer plus spatial UI schema out, scores computed in code.

Built 27 Nov 2026 as an independent pre-application prototype for ECL Virtual Intern Program Jan 2027, Project 4, "Developing Context-Aware LLM Interaction Techniques for Mixed Reality", collaborator Lefan Lai. It is not part of ECL, not endorsed by Lefan Lai, and not an ECL acceptance.

## The gap

Lai CHI 2026 shows complex environments and varied virtual depth impair visual search in MR, depth cues can compensate, a secondary auditory task raises perceived workload without changing search time, and implicit memory for repeated spatial layouts stays robust under load. VIGOR, co-authored by Lefan Lai, shows multimodal LLMs hallucinate objects because fixed-resolution visual encoding gives limited fine-grained grounding, and proposes a training-free selective coarse-to-fine check with a global yes-no margin and local refinement on uncertain cases. No verified source provides a reproducible, headset-free test that holds the user query fixed while changing only the spatial scene, checks whether the LLM mentions objects that are not in that scene, and checks whether its UI schema respects Lai depth and spatial-regularity rules. This harness is that test, in Python, without a headset.

Sources:
- Lai et al., CHI 2026, "Searching Through Complex Worlds", DOI 10.1145/3772318.3790976, https://arxiv.org/html/2602.18669v1
- Li et al., EMNLP 2026 Findings, VIGOR, https://aclanthology.org/2026.findings-emnlp.72/
- ECL VIP Jan 2027, https://empathiccomputing.org/virtual-intern-program/

## How it works

1. A scene is a synthetic JSON file in data/scenes: objects with x, y, z in metres, distance_m, depth_layer (near under 0.8 m, mid 0.8 to 1.6 m, far over 1.6 m), occluded flag, gaze_target flag.
2. Two prompts are built from the same query: blind (query only, no scene) and context-aware (query plus scene JSON plus spatial relations computed in code plus Lai rules: use depth as a grouping cue, keep repeated layouts stable, no UI for occluded objects).
3. The LLM is called through one interface with two backends: mock (deterministic, for CI) and live (OpenAI-compatible API, key from the OPENAI_API_KEY environment variable only, never in code).
4. The output is parsed into answer text, spatial claims, and a UI schema. Invalid schema is scored as a schema failure, not silently fixed.
5. Verification runs in code, not by asking the LLM to check itself: object existence against the scene JSON, spatial claims against x, y, z and distance, UI anchors against occluded or absent objects.
6. VIGOR gate, deterministic mock analogue: for each candidate object a yes/no score pair is assigned by a fixed rule from scene state (present and visible 0.92/0.08, present and occluded 0.55/0.45, absent 0.30/0.70), margin m = z_yes - z_no, threshold 0.30. Margin below threshold triggers a re-check, a second lookup of the scene JSON in code. The object is kept only if the re-check confirms it is present and visible. This is a mock analogue, NOT real MLLM logits, and NOT VIGOR paper code. No VIGOR code was found.

## Dataset

12 hand-written synthetic JSON scenes, desk 3, kitchen 3, lab bench 3, office 3, in data/scenes. At least 4 paired scenes share the same query and differ in only one scene fact. In fact there are 8 defined pairs in mr_context/eval.py: moved near to far, removed object, occluded target, gaze changed, repeated layout with one swap. No real photos, no headset captures, no scraped MR data.

Synonyms in data/synonyms.json are applied with word-boundary matching only. A correct denial ("There is no blue mug") is not counted as a hallucination: the object is named to say it is absent, which is the right answer.

## Run it

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m mr_context.eval --mode mock
.venv/bin/uvicorn mr_context.app:app --reload
```

On Windows use `.venv\Scripts\python` instead of `.venv/bin/python`. The live backend needs `OPENAI_API_KEY` set in the environment, plus optional `OPENAI_BASE_URL` and `MR_LLM_MODEL` (default gpt-4o-mini). Without a key, `--mode live` fails with a clear error and nothing is sent.

API: GET /health, GET /scenes, GET /scenes/{scene_id}, POST /evaluate with {scene, mode, backend}. The demo UI at http://127.0.0.1:8000/ shows blind vs context-aware side by side for one scene. It is a plain web page, explicitly not Unity.

Layout note: the package lives at the repo root as mr_context/, not src/mr_context/, so the run commands above work without PYTHONPATH. That is the only deviation from the plan file list.

## Results, mock run, 27 Nov 2026

Run: `.venv/bin/python -m mr_context.eval --mode mock`, n = 12 scenes, model mock-deterministic-v1, date 2026-11-27. Full table in results/results.md, raw data in results/results.json. All 12 scenes reported, no cherry-picking.

- Mean groundedness blind 0.278, context 1.0
- Mean hallucination rate blind 0.723, context 0.0
- Spatial accuracy context 1.0 on all 12 scenes, blind 0.0 on all 12
- Paired scenes: context answer changed in 7 of 8, blind answer changed in 0 of 8. The one unchanged context pair is scene_10 vs scene_11: the swap was desk plant for desk lamp, neither is the laptop nearest neighbour (keyboard is), so the target answer correctly stays stable. That is spatial-regularity stability, not insensitivity.

Read these numbers honestly. The mock backend is a deterministic stand-in. Blind mode gets no scene, context mode gets the scene, so the mock delta is a property of that construction, not evidence about a real LLM. A live run with a real model is needed to measure a real delta. The mock run proves the verification pipeline works: it flags hallucinated objects, wrong near/far claims, occluded UI anchors, and invalid schemas, and it shows the answer changing when the scene changes.

## Tests

`.venv/bin/python -m pytest -q` on 27 Nov 2026: 34 passed, 0 failed. Tests cover verification (hallucinated object, wrong near/far, occluded UI anchor, absent UI anchor, invalid schema, correct denial), prompts and the VIGOR gate, the eval runner (12 scenes, 3 per domain, 8 pairs, mock context beats blind), and the API (health, evaluate context and blind, bad mode, scenes list).

## What this is NOT

- No Unity experience, no Unity prototype, no MR headset test, no Meta Quest 3 test, no real user study, no NASA-TLX scores, no EEG or physiological data.
- No claim that synthetic JSON scenes generalise to real MR scenes. Transfer to Unity and headset testing is the Jan 2027 internship work, not this prototype.
- No claim that Lefan Lai endorsed this prototype, or that ECL accepted it, or that it is part of ECL. It is an independent prototype built from public papers.
- No claim of a publication. The output is a repo plus an evaluation report, not a paper.
- No live LLM run was done in this build. No API key was used, no key is stored anywhere. Live results are still unverified.

## Demo

demo/VIDEO_SCRIPT.md is a 90-second video script outline. No video was recorded and no screenshots were captured in this local build. demo/SCREENSHOTS.md says so plainly and describes what each of the 3 screenshots would show. Do not treat those descriptions as captured images.
