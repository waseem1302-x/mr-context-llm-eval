# mr-context-llm-eval results

Backend: mock, model: mock-deterministic-v1, date: 2026-11-27, n: 12 scenes

Mean groundedness blind: 0.278, context: 1.0
Mean hallucination blind: 0.723, context: 0.0
Paired scenes: 8, context answer changed in 7, blind answer changed in 0

Mock note: the mock backend is a deterministic stand-in. Blind mode gets no scene, context mode gets the scene, so the mock delta is a property of that construction, not evidence about a real LLM. A live run is needed to measure a real delta.

| scene | domain | grounded blind | grounded context | halluc blind | halluc context | spatial blind | spatial context | schema context |
|---|---|---|---|---|---|---|---|---|
| scene_01_desk | desk | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_02_desk | desk | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_03_desk | desk | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | True |
| scene_04_kitchen | kitchen | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_05_kitchen | kitchen | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_06_kitchen | kitchen | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | True |
| scene_07_lab | lab bench | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_08_lab | lab bench | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_09_lab | lab bench | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_10_office | office | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_11_office | office | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |
| scene_12_office | office | 0.333 | 1.0 | 0.667 | 0.0 | 0.0 | 1.0 | True |

## Paired scenes

- scene_01_desk vs scene_02_desk (blue mug moved near to far): context answer changed: True, blind answer changed: False
- scene_01_desk vs scene_03_desk (blue mug removed): context answer changed: True, blind answer changed: False
- scene_04_kitchen vs scene_05_kitchen (red kettle occluded): context answer changed: True, blind answer changed: False
- scene_04_kitchen vs scene_06_kitchen (red kettle removed): context answer changed: True, blind answer changed: False
- scene_07_lab vs scene_08_lab (pipette rack swapped for test tube rack): context answer changed: True, blind answer changed: False
- scene_07_lab vs scene_09_lab (gaze target changed): context answer changed: True, blind answer changed: False
- scene_10_office vs scene_11_office (desk plant swapped for desk lamp): context answer changed: False, blind answer changed: False
- scene_10_office vs scene_12_office (gaze target changed): context answer changed: True, blind answer changed: False

## All answers (no cherry-picking)

### scene_01_desk (desk)
Query: Where is the blue mug and what is next to it?
Blind: The blue mug is near the notebook and the phone. The blue mug is on the left side, near the notebook.
Context: The blue mug is near the laptop, in the near depth layer. The laptop is the closest visible object to it.

### scene_02_desk (desk)
Query: Where is the blue mug and what is next to it?
Blind: The blue mug is near the notebook and the phone. The blue mug is on the left side, near the notebook.
Context: The blue mug is far from the book stack, in the far depth layer. The book stack is the closest visible object to it.

### scene_03_desk (desk)
Query: Where is the blue mug and what is next to it?
Blind: The blue mug is near the notebook and the phone. The blue mug is on the left side, near the notebook.
Context: There is no blue mug in this scene. I cannot point to it, and no UI element is shown for it.

### scene_04_kitchen (kitchen)
Query: Where is the red kettle and what is next to it?
Blind: The red kettle is near the notebook and the phone. The red kettle is on the left side, near the notebook.
Context: The red kettle is near the stove, in the near depth layer. The stove is the closest visible object to it.

### scene_05_kitchen (kitchen)
Query: Where is the red kettle and what is next to it?
Blind: The red kettle is near the notebook and the phone. The red kettle is on the left side, near the notebook.
Context: The red kettle is in this scene but it is occluded, so it is not shown in the UI. I will not place a label on it.

### scene_06_kitchen (kitchen)
Query: Where is the red kettle and what is next to it?
Blind: The red kettle is near the notebook and the phone. The red kettle is on the left side, near the notebook.
Context: There is no red kettle in this scene. I cannot point to it, and no UI element is shown for it.

### scene_07_lab (lab bench)
Query: Where is the microscope slide box and what is next to it?
Blind: The microscope slide box is near the notebook and the phone. The microscope slide box is on the left side, near the notebook.
Context: The microscope slide box is near the pipette rack, in the near depth layer. The pipette rack is the closest visible object to it.

### scene_08_lab (lab bench)
Query: Where is the microscope slide box and what is next to it?
Blind: The microscope slide box is near the notebook and the phone. The microscope slide box is on the left side, near the notebook.
Context: The microscope slide box is near the test tube rack, in the near depth layer. The test tube rack is the closest visible object to it.

### scene_09_lab (lab bench)
Query: Where is the microscope slide box and what is next to it?
Blind: The microscope slide box is near the notebook and the phone. The microscope slide box is on the left side, near the notebook.
Context: The microscope slide box is near the pipette rack, in the near depth layer. The pipette rack is the closest visible object to it. You are looking at the centrifuge.

### scene_10_office (office)
Query: Where is the laptop and what is next to it?
Blind: The laptop is near the notebook and the phone. The laptop is on the left side, near the notebook.
Context: The laptop is near the keyboard, in the near depth layer. The keyboard is the closest visible object to it.

### scene_11_office (office)
Query: Where is the laptop and what is next to it?
Blind: The laptop is near the notebook and the phone. The laptop is on the left side, near the notebook.
Context: The laptop is near the keyboard, in the near depth layer. The keyboard is the closest visible object to it.

### scene_12_office (office)
Query: Where is the laptop and what is next to it?
Blind: The laptop is near the notebook and the phone. The laptop is on the left side, near the notebook.
Context: The laptop is near the keyboard, in the near depth layer. The keyboard is the closest visible object to it. You are looking at the monitor.
