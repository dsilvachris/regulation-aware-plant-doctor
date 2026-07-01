import json
corpus = json.load(open("corpus.json"))
no_entries = json.load(open("corpus_no_entries.json"))
corpus.extend(no_entries)
json.dump(corpus, open("corpus.json", "w"), indent=2, ensure_ascii=False)
print(f"Corpus now {len(corpus)} entries")   # should be 15