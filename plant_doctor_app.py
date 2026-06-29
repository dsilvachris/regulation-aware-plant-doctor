"""
plant_doctor_app.py — Step 6: multimodal front-end (TFLite version, no TensorFlow needed).
Image -> disease (MobileNetV2, TFLite) -> bridge -> grounded, BVL-aware advice (local LLM).

Faithfulness built in at two points:
  - confidence gate : if the vision model is unsure, ABSTAIN
  - bridge          : 'healthy' and out-of-corpus diseases ABSTAIN instead of mis-advising

Needs in the same folder:
  agro_vision.tflite, agro_vision_classes.json, vision_to_corpus.json, corpus.json
Prereqs: Ollama running; pip install ai-edge-litert gradio pillow ollama numpy
"""
import json
import numpy as np
from PIL import Image
import ollama
import gradio as gr
from ai_edge_litert.interpreter import Interpreter   # light TFLite runtime (no TensorFlow)

# --- config (tune these) ---
MODEL_LLM      = "llama3.2:3b"   # snappy for a demo; "llama3.1:8b" for richer advice (slower)
CONF_THRESHOLD = 0.50           # below this, abstain. Field model is ~50% acc, so it WILL abstain often (honest).
IMG            = 128

# --- load the TFLite model ---
interpreter = Interpreter(model_path="agro_vision.tflite")
interpreter.allocate_tensors()
inp_detail  = interpreter.get_input_details()[0]
out_detail  = interpreter.get_output_details()[0]

class_names = json.load(open("agro_vision_classes.json", encoding="utf-8"))
bridge      = {k: v for k, v in json.load(open("vision_to_corpus.json", encoding="utf-8")).items()
               if not k.startswith("_")}
corpus      = {r["id"]: r for r in json.load(open("corpus.json", encoding="utf-8"))}
print(f"Loaded TFLite model ({len(class_names)} classes), bridge ({len(bridge)}), corpus ({len(corpus)})")

def classify(pil_img):
    """Return top-3 (label, prob). The model's first layer rescales internally, so feed raw 0-255 float32."""
    im = pil_img.convert("RGB").resize((IMG, IMG))
    x = np.array(im, dtype=np.float32)[None, ...]          # (1,128,128,3)
    interpreter.set_tensor(inp_detail["index"], x)
    interpreter.invoke()
    probs = interpreter.get_tensor(out_detail["index"])[0]
    order = np.argsort(probs)[::-1][:3]
    return [(class_names[i], float(probs[i])) for i in order]

def ground_with_llm(rec):
    prompt = f"""You are a plant-disease assistant for growers in Germany.
A plant photo has been identified as: {rec['disease']} ({rec['pathogen']}).
Using ONLY the facts in the context below, explain what the problem is and how to manage it.
Do NOT add any information that is not in the context.
If the context mentions BVL-authorised products, include that point.

Context:
{rec['text']}

Answer:"""
    return ollama.generate(model=MODEL_LLM, prompt=prompt)["response"].strip()

def diagnose(pil_img):
    if pil_img is None:
        return "Please upload a leaf photo."
    top3 = classify(pil_img)
    label, conf = top3[0]

    # (1) CONFIDENCE GATE
    if conf < CONF_THRESHOLD:
        out = [f"### Not confident enough to advise",
               f"Top guess: **{label}** ({conf:.0%}) - below the {CONF_THRESHOLD:.0%} confidence bar.",
               "Field photos are hard; the model is unsure. Most likely possibilities:"]
        out += [f"- {n} ({p:.0%})" for n, p in top3]
        out.append("\nTry a clearer, well-lit photo of a single leaf, or consult a local expert.")
        return "\n".join(out)

    entry = bridge.get(label, {"action": "abstain", "reason": "unmapped class"})

    if entry["action"] == "healthy":
        return (f"### Looks healthy\n"
                f"Detected: **{label}** ({conf:.0%}). No disease identified - no treatment needed.")

    if entry["action"] == "abstain":
        return (f"### Identified, but outside my authorised guidance\n"
                f"Detected: **{label}** ({conf:.0%}).\n\n"
                f"I recognise this, but it is not in my authorised knowledge base "
                f"({entry.get('reason','out of scope')}), so I will not give treatment advice. "
                f"Please consult official local guidance or an expert.")

    # action == "ground"
    rec = corpus[entry["corpus_id"]]
    advice = ground_with_llm(rec)
    return (f"### {rec['disease']} - {rec['pathogen']} ({rec['pathogen_type']})\n"
            f"Vision confidence: {conf:.0%}\n\n"
            f"{advice}\n\n"
            f"---\n*Grounded on EPPO {rec['eppo_code']} - source: {rec['source']}. "
            f"In Germany, only BVL-authorised products may be used, and that list changes over time.*")

demo = gr.Interface(
    fn=diagnose,
    inputs=gr.Image(type="pil", label="Upload a leaf photo"),
    outputs=gr.Markdown(label="Diagnosis & grounded advice"),
    title="Regulation-Aware Plant Doctor",
    description=("Image -> disease (MobileNetV2 transfer learning) -> grounded, BVL-aware advice (local RAG). "
                 "Abstains when the model is unsure or the disease is outside its authorised corpus."),
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()   # add share=True for a temporary public link