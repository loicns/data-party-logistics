# Backlog & Follow-ups

Decisions deferred, tools to monitor, and tasks scheduled for a future date.

---

## Open

- [ ] **Evaluate no-added-cost supply-chain shortage intelligence**
  Build a backlog spike for explainable early-warning signals around fuel,
  circuits/electronics, food, autos, and other supply-chain exposure using the
  current AIS, port congestion, weather, NOAA, and GDELT data plane.
  → Artifact: `/Users/loicns/Downloads/supply-chain-shortage-prediction-artifact.html`
  → Action: start with vessel-type, port-specialization, and route-archetype
  mappings; publish risk scores with reason codes and confidence labels.
  → Constraint: do not claim exact cargo, importer, SKU, or inventory shortage
  prediction unless manifest, customs, carrier, or customer data is deliberately
  added later.
  *Priority: Medium — useful market wedge after the current congestion forecast
  surface is stable.*

- [ ] **Monitor mkdocs-material / MkDocs 2.0 compatibility**
  The Material maintainer has warned against MkDocs 2.0 due to breaking changes
  (plugin removal, no migration path, no license yet).
  → Check: https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
  → Action before any `uv lock --upgrade`: pin `mkdocs` + `mkdocs-material` versions first.
  *Priority: Low — revisit before next dependency upgrade cycle.*

---

## Done

<!-- Move resolved items here with [x] -->
