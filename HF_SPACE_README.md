---
title: Regulation-Aware Plant Doctor
emoji: 🌱
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Regulation-Aware Plant Doctor

A conversational, region-aware plant-disease assistant for Germany and Norway, grounded in a curated
knowledge graph for its 3 most rigorously validated diseases (late blight, apple scab, cucurbit powdery
mildew) and document retrieval elsewhere — with an explicit, disclosed boundary between the two, and a
deterministic verification layer that flags any claim it can't trace back to its retrieved facts.

Upload a leaf photo or describe symptoms in the chat. The assistant will ask which country you're in if
it isn't clear — advice differs by region.

**Research background:** this is Phase 5 of a larger research programme validating when a knowledge
graph, versus document-RAG, versus an LLM router, actually improves regulatory-advice reliability. Full
methodology: https://github.com/dsilvachris/regulation-aware-plant-doctor

**This is a research/portfolio project, not a deployable agricultural advisory tool.** Always verify
against BVL (Germany) or Mattilsynet (Norway) directly before acting on any advice.