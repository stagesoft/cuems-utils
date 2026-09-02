# pre-008 corpus — retained originals

**Feature**: `008-rebuild-extension` | **Task**: T003 | **Frozen**: 2026-08-28, before any
Phase 1 schema edit.

This is a byte-for-byte snapshot of `tests/data/corpus/` as it stood immediately before ITEM A's
first schema edit (T013). It exists because ITEM A and ITEM D rewrite `tests/golden/` **and**
`tests/data/corpus/` itself (T023, T076) to the new wire shapes — old-shape `<duration>TC</duration>`
text, `fade_in`/`fade_out` action types, `<fade_profiles>` — so once those tasks land, nowhere else in
the tree still holds a real document in the pre-008 shape.

**This directory is ITEM E's conversion fixture set (FR-011).** Every document here is deliberately
**invalid** against the post-feature schemas — that is the point, not a defect — which is why
`tests/contract/test_pre008_corpus_retained.py` (T004) asserts only that these files **parse**
(well-formedness) and never that they **validate** against the current bundled schemas.

**Never regenerated.** Per the corpus's own refresh rule (`tests/data/corpus/PROVENANCE.md`, FR-021)
and standing rule 8, nothing here is rewritten to make a test pass. `PROVENANCE.md` itself and
`negative/README.md` were not copied — they are corpus *documentation*, not fixtures, and are not
subject to "well-formedness only" parsing.

Two more fixtures are added later, by construction rather than copy, because no document in the
original corpus carries their shape:

- `fade_actions.xml` (T080) — `fade_in`/`fade_out` action cues; the corpus holds only `fade_action`
  and `play`.
- `script_v1_all_transforms.xml` (T080a) — all three `script` 1→2 transformations at once (old-shape
  duration, both retired `action_type` values, and a `fade_profiles` block); no single document in the
  tree combines all three.
