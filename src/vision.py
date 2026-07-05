"""
vision.py — TFLite leaf-image identifier for the chat.

Returns a structured result the conversation engine can act on:
  {action: "ground"|"healthy"|"abstain"|"lowconf", label, conf, top3,
   corpus_id?, reason?, crop?}

Confidence-gated and bridged to the corpus — the same logic as the Gradio app, exposed
as a function so the chat can call it. Kept separate so the text chat doesn't need TFLite.
"""
import json
from pathlib import Path
import numpy as np
from ai_edge_litert.interpreter import Interpreter

ROOT = Path(__file__).resolve().parent.parent
DATA, MODELS = ROOT / "data", ROOT / "models"
IMG = 128
CONF_THRESHOLD = 0.50

_interp = Interpreter(model_path=str(MODELS / "agro_vision.tflite"))
_interp.allocate_tensors()
_IN = _interp.get_input_details()[0]
_OUT = _interp.get_output_details()[0]
_classes = json.load(open(DATA / "agro_vision_classes.json", encoding="utf-8"))
_bridge = {k: v for k, v in json.load(open(DATA / "vision_to_corpus.json", encoding="utf-8")).items()
           if not k.startswith("_")}

def classify(pil_img):
    im = pil_img.convert("RGB").resize((IMG, IMG))
    x = np.array(im, dtype=np.float32)[None, ...]
    _interp.set_tensor(_IN["index"], x)
    _interp.invoke()
    probs = _interp.get_tensor(_OUT["index"])[0]
    order = np.argsort(probs)[::-1][:3]
    return [(_classes[i], float(probs[i])) for i in order]

def identify(pil_img):
    """Run the vision model + confidence gate + bridge; return a structured result."""
    top3 = classify(pil_img)
    label, conf = top3[0]
    if conf < CONF_THRESHOLD:
        return {"action": "lowconf", "label": label, "conf": conf, "top3": top3}
    entry = _bridge.get(label, {"action": "abstain", "reason": "unmapped class"})
    return {"action": entry["action"], "label": label, "conf": conf, "top3": top3,
            "corpus_id": entry.get("corpus_id"), "reason": entry.get("reason"),
            "crop": entry.get("crop")}