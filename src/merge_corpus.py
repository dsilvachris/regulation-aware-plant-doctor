from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent
DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'
import json
corpus = json.load(open(str(DATA / "corpus.json")))
no_entries = json.load(open(str(DATA / "corpus_no_entries.json")))
corpus.extend(no_entries)
json.dump(corpus, open(str(DATA / "corpus.json"), "w"), indent=2, ensure_ascii=False)
print(f"Corpus now {len(corpus)} entries")   # should be 15