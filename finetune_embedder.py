"""
finetune_embedder.py — Step 5, Phase 2.
Fine-tune all-MiniLM-L6-v2 on (query -> correct disease text) pairs so it separates
closely-related diseases (e.g. late vs early blight) better than the general model.

Uses MultipleNegativesRankingLoss: for each (query, correct-text) pair in a batch,
every OTHER disease text in the batch is treated as a negative to push away.

Prereqs: pip install sentence-transformers torch
Trains in ~1-2 min on a Mac (CPU/MPS); no GPU needed. Saves to ./finetuned-agri-embedder
"""
import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# --- Data: pair each training query with its disease's corpus text ---
corpus = {r["id"]: r["text"] for r in json.load(open("corpus.json", encoding="utf-8"))}
train  = json.load(open("train_queries.json", encoding="utf-8"))

examples = [InputExample(texts=[t["query"], corpus[t["disease_id"]]]) for t in train]
print(f"{len(examples)} training pairs across {len(corpus)} diseases")

# --- Model + contrastive loss ---
model = SentenceTransformer("all-MiniLM-L6-v2")          # start from the general embedder
loader = DataLoader(examples, shuffle=True, batch_size=16)
loss   = losses.MultipleNegativesRankingLoss(model)

# --- Train ---
EPOCHS = 4
model.fit(
    train_objectives=[(loader, loss)],
    epochs=EPOCHS,
    warmup_steps=10,
    show_progress_bar=True,
)

OUT = "finetuned-agri-embedder"
model.save(OUT)
print(f"\nSaved fine-tuned model -> ./{OUT}")

# --- Tiny sanity check: does 'late blight' now sit closer to the late-blight text? ---
import numpy as np
def sim(a, b):
    ea, eb = model.encode([a, b], normalize_embeddings=True)
    return float(ea @ eb)

q = "my tomato leaves have grey-green water-soaked patches spreading fast in cool wet weather"
late  = corpus["tomato_potato_late_blight"]
early = corpus["tomato_potato_early_blight"]
print("\nSanity check (late-blight-style query):")
print(f"  similarity to LATE  blight text: {sim(q, late):.3f}")
print(f"  similarity to EARLY blight text: {sim(q, early):.3f}")
print("  (we want LATE > EARLY by a clear margin)")