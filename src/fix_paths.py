"""
fix_paths.py — one-time patcher: makes every script in src/ resolve data/models/results
paths relative to the project root, so they run correctly after the folder reorganisation.
Run it ONCE from the project root:  python src/fix_paths.py
It skips plant_doctor_app.py (already fixed), fix_paths.py itself, and exp_plantdoc_dataset.py.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent           # the src/ folder
SKIP = {"plant_doctor_app.py", "fix_paths.py", "exp_plantdoc_dataset.py"}

DATA_FILES = ["corpus_no_entries.json", "corpus.json", "eval_set.json",
              "region_eval_set.json", "region_probe_set.json", "vision_to_corpus.json",
              "agro_vision_classes.json", "train_queries_clean.json", "train_queries.json"]
MODEL_FILES = ["finetuned-agri-embedder"]
RESULT_FILES = ["eval_scores.csv", "eval_results.md",
                "strengthen_results.json", "strengthen_results.md", "region_eval_results.json"]

HEADER = (
    "from pathlib import Path as _Path\n"
    "_ROOT = _Path(__file__).resolve().parent.parent\n"
    "DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'\n"
)

def insert_header(src):
    if "_ROOT = _Path(__file__)" in src:       # already patched
        return src
    m = re.match(r'\s*(?:"""|\'\'\')', src)
    if m:                                       # has a module docstring: insert after it
        q = src[m.start():m.start()+3]
        end = src.find(q, m.start()+3)
        end = src.find("\n", end) + 1
        return src[:end] + HEADER + src[end:]
    return HEADER + src                         # no docstring: prepend

def patch(src):
    src = insert_header(src)
    for f in DATA_FILES:
        src = src.replace(f'"{f}"', f'str(DATA / "{f}")').replace(f"'{f}'", f'str(DATA / "{f}")')
    for f in MODEL_FILES:
        src = src.replace(f'"{f}"', f'str(MODELS / "{f}")').replace(f"'{f}'", f'str(MODELS / "{f}")')
    for f in RESULT_FILES:
        src = src.replace(f'"{f}"', f'str(RESULTS / "{f}")').replace(f"'{f}'", f'str(RESULTS / "{f}")')
    return src

changed = []
for p in sorted(SRC.glob("*.py")):
    if p.name in SKIP:
        continue
    original = p.read_text(encoding="utf-8")
    patched = patch(original)
    if patched != original:
        p.write_text(patched, encoding="utf-8")
        changed.append(p.name)
print(f"Patched {len(changed)} scripts:", ", ".join(changed) if changed else "(none)")