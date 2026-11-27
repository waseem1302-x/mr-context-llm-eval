# 90-second demo video script

No video was recorded in this local build. This is a script outline only, for a future recording. Total 90 seconds, no face cam needed.

0-10s: Terminal. Run `.venv/bin/python -m pytest -q`. Show 34 passed, 0 failed.
10-25s: Terminal. Run `.venv/bin/python -m mr_context.eval --mode mock`. Show mean groundedness blind 0.278, context 1.0, pairs context changed 7 of 8.
25-40s: Terminal. Start `.venv/bin/uvicorn mr_context.app:app`. Open http://127.0.0.1:8000/docs, show POST /evaluate.
40-70s: Demo UI at http://127.0.0.1:8000/. Pick scene_01_desk, run both. Blind answer mentions notebook and phone, which are not in the scene. Context answer says the blue mug is near the laptop, in the near depth layer. Pick scene_02_desk, same query, mug moved far: context answer changes to far from the book stack, blind answer does not change.
70-90s: results/results.md table. All 12 scenes, blind vs context side by side. Close with the honest limit line: mock backend only, no headset, no Unity, live run still to do.
