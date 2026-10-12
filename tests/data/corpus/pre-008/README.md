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

## One exception to "never regenerated", recorded rather than quiet

**Feature 013, T050.** `script_v1_all_transforms.xml`'s one `<AudioCue>` is now
`<Cue class="audio">`. Nothing else in the file changed, and its `doc_version` is still absent
(version 1), so all three 1→2 transformations are still exactly what it exercises.

Why it had to move, since "`pre-008/` is not touched" is what T050 says. The device shape is
**orthogonal to `doc_version`** — feature 013 takes no version step (FR-020) — so a document can be
version 1 in either device shape. A version-1 document in the *old* device shape is one that neither
tool can migrate on its own: `cuems-reshape-devices` validates the reshaped tree and sees a
version-1 `<duration>`, while `cuems-convert-documents` validates after converting and sees
old-shape cues. The reshape tool resolves that by validating the document *as the load path will see
it* — registered conversions applied to a throwaway copy, nothing written — which fixes the
migration order at **reshape, then convert**. This fixture is the version-1 half of that pair, so it
is carried in the new device shape; the old-shape fixtures the reshape tool is tested against live in
`pre-013/`, which does stay old-shape.

Every other file here is untouched. The snapshot copies that still carry `<AudioCue>` and friends
are never loaded — `test_pre008_corpus_retained.py` asserts only that they parse — so they keep
their byte-for-byte provenance.
