# Strengthen — repeated-run refusal metrics

10 runs per condition. Auto-measured from answer text (no grading).


**v1_3B_strict** (llama3.2:3b)
- over-refusal (in-corpus wrongly refused): 34% (range 29-38%, raw 6-8/21)
- ooc-refused (correctly refused): 92% (range 75-100%, raw 3-4/4)
- raw over-refusal counts: [8, 7, 8, 7, 6, 7, 7, 7, 7, 7]

**v3_8B_revised** (llama3.1:8b)
- over-refusal (in-corpus wrongly refused): 33% (range 24-38%, raw 5-8/21)
- ooc-refused (correctly refused): 52% (range 50-75%, raw 2-3/4)
- raw over-refusal counts: [7, 6, 8, 7, 6, 7, 8, 7, 5, 8]