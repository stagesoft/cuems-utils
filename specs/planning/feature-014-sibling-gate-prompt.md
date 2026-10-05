<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Agent prompt — feature 014's sibling gates (T028–T032)

> ## ✅ ALL FIVE GATES ARE DONE — 2026-10-05. This prompt is spent.
>
> Nothing here needs running. It is kept as the **record of what was asked and what came back**, and
> as the working template for the next cross-repository gate round: the structure held, and the five
> corrections it accumulated while in use (below) are the part worth reusing.
>
> | Gate | Repository | Commit | Arm C |
> |---|---|---|---|
> | T028 | `cuems-engine` | `9fce7e6` | 1 failed / 922 passed (pre-existing, environment) |
> | T029 | `cuems-power-bridge` | `dd1256f` | 276 / 0 |
> | T030 | `cuems-nodeconf` | `61c5705` | 174 / 174 |
> | T031 | `cuems-common` | `e595e67` | 104 / 104 |
> | T032 | `cuems-editor` | `22093fd` | 161 passed / 2 skipped |
>
> **Result: eight failures attributable to feature 014 across five repositories, against 183 that
> were already there.** Recorded per repository in
> `../014-xs-boolean-and-media-elements/baseline.md` §8 (T033, complete).
>
> **Five things this prompt got wrong and had corrected while sessions used it**, which is the
> reusable part — a cross-repository prompt is wrong until it has been run:
> 1. it told every session to switch one **shared** `../cuems-utils` checkout, racing by
>    construction (caught by T030, fixed to a per-session worktree, confirmed by T029);
> 2. it said `cuems-convert-documents` takes a **directory** — it takes files;
> 3. it under-counted `cuems-common` by one document and sent it after a **mirrored XSD that no
>    longer exists**;
> 4. it enumerated refusal fixtures instead of stating the **rule**, and missed two of three;
> 5. it did not know the tool **destroys XML comments** (found by T031, confirmed by T028), nor that
>    §4.5's migration order has a **third case** (found by T028).
>
> Every one was found by a session *using* it, not by review here. **Delete this file with T036**,
> or keep it as the template — but do not point a new session at it expecting work to be left.

**One prompt, five repositories, five independent sessions.** Copy everything between the
`>>> BEGIN` and `<<< END` markers into a **fresh** Claude Code session opened in the sibling
repository you want done. The prompt identifies which repository it is in and routes itself; do not
edit it per repository.

**Run them one repository per session.** They are `[P]` in `tasks.md` because they touch different
trees, and a single session doing two of them loses the thing the split exists for — a per-repository
measurement that can be reported as red with a reason rather than averaged away.

**Which sessions to open** (`cuems-frontend` is *not* one of them — its share is T034, its own
`06-amendment-feature-014.md` is the authority, and it is an Angular repo with no Python suite):

| Session opened in | Gate | Rough size | State |
|---|---|---|---|
| `cuems-engine` | T028 | — | ✅ done 2026-10-05 (`9fce7e6`) |
| `cuems-nodeconf` | T030 | — | ✅ done 2026-10-05 (`61c5705`) |
| `cuems-editor` | T032 | — | ✅ done 2026-10-05 (`22093fd`) |
| `cuems-power-bridge` | T029 | — | ✅ done 2026-10-05 (`dd1256f`) |
| `cuems-common` | T031 | — | ✅ done 2026-10-05 (`e595e67`) |

**All five are done.** Their reports are worth reading for what they returned:

- **`cuems-nodeconf`** found a `settings` migration dead end and a race in this prompt, both since
  fixed.
- **`cuems-power-bridge`** confirmed the dead end independently (9 of 9 of its settings fixtures)
  and produced the cleanest result in the set: **arms A and B identical**, so 014 caused zero
  failures there.
- **`cuems-editor`** closed its own T059 in the same session, resolving UR-5.
- **`cuems-common`** found that `cuems-convert-documents` **silently destroys every XML comment**,
  and hand-rewrote its annotated example rather than losing them — see §3.
- **`cuems-engine`** found the **third migration order** §4.5 did not cover (an already-`doc_version="2"`
  document with old booleans *and* old device shape: hand-fix booleans, *then* reshape), closed
  §4.2's long-outstanding item 9, and confirmed the comment loss a second time.

**What three landed gates have established, and the open two should expect:** most of arm B is
probably **not 014**. Across the three, **six failures were attributable to this feature and 87
were pre-existing** — nearly all of them 013's device shape, never migrated in the siblings. Take
arm A.

**After all five report**, T033–T036 are done back in `cuems-utils` — T033 records every arm in
`specs/014-xs-boolean-and-media-elements/baseline.md`, T034 the frontend hand-off, T035 deletes
`specs/planning/booltype-silent-false-coercion-defect.md`, T036 is the closing documentation pass.
Those are **not** in this prompt, and no sibling session should attempt them.

---

>>> BEGIN — copy from here

You are working in one of the CUEMS sibling repositories. Upstream, `cuems-utils` has landed
feature **014** (`xs:boolean`, the four media elements, the two curve names, the public
configuration ingestion) on its branch `014-xs-boolean-and-media-elements`. Your job is **this
repository's gate** for that feature.

## 0. Read these first, in this order

1. `../cuems-utils/specs/014-xs-boolean-and-media-elements/migration-guide.md` — **the authority**.
   It is also the rule-4 release note. §4.1 names your paths; §4.2 is the version-2 problem; §4.4 is
   when the old form stops being accepted; §4.5 is the tool order.
2. `./CLAUDE.md` — **this** repository's own conventions, especially how to run its suite and
   whether its commits are GPG-signed.
3. `../cuems-utils/specs/014-xs-boolean-and-media-elements/tasks.md`, the section
   **"The sibling gates (E3)"** — your gate's task text, including corrections dated 2026-10-05.

## 1. What actually changed, in one paragraph

`cms:BoolType` (an `xs:string` enumeration of `True`/`False`) is now the standard `xs:boolean`. XML
text is `true`/`false`; the JSON wire carries real booleans. It affects exactly five elements —
`<autoload>`, `<enabled>`, `<timecode>` in `script.xsd` and `<adopted>`, `<online>` in
`network_map.xsd` — so **only `script.xml` and `network_map.xml` documents are affected**. No
`settings.xml`, no `mappings.xml`, no project `settings.xml`: those schemas declare no boolean
(verified against all five). There is **no new schema version**: the rewrite rides the existing,
unreleased `script` 1 → 2 and `network_map` 1 → 2 steps, and `cuemsutils` stays at `0.1.0rc16`, so
**no dependency bound anywhere needs touching** — every sibling already declares
`>=0.1.0rc16,<0.1.1`.

**You almost certainly need no source change.** Your code holds objects, and those were always real
`bool`s. What breaks is **fixtures and data** — which is the lesson features 012 and 013 each
learned once: the breakage lives where a call-site census cannot see it.

## 2. Step zero — identify yourself and pin the library

```bash
basename "$(git rev-parse --show-toplevel)"   # which repository am I?
git branch --show-current                      # expect: feat/xml-refactor
```

Then confirm your suite resolves `cuemsutils` to the sibling working tree on the 014 branch. **Do
not proceed until this is true** — a pass measured against an installed `rc16` from PyPI measures
nothing:

```bash
git -C ../cuems-utils branch --show-current     # expect: 014-xs-boolean-and-media-elements
# then, using THIS repository's own runner (see its CLAUDE.md — poetry, hatch or plain pytest):
<runner> python -c "import cuemsutils, pathlib; print(cuemsutils.__version__, cuemsutils.__file__)"
# expect: 0.1.0rc16 and a path under .../cuems-utils/src/cuemsutils/
```

If it resolves to a site-packages copy instead, say so and stop rather than working around it. That
is a finding, not an obstacle to route past.

⚠ On this development box bare `uvx` fails through the pyenv shim. Use
`~/.pyenv/versions/3.11.9/bin/uvx` if your repository's runner needs it.

## 3. The tools, and the one thing everyone gets wrong about them

Both live in `cuems-utils`. Use its **console scripts**, which its hatch environment installs:

```bash
UBIN=$(cd ../cuems-utils && ~/.pyenv/versions/3.11.9/bin/uvx hatch env find test.py3.11)/bin
ls "$UBIN" | grep cuems      # expect: cuems-convert-documents, cuems-init-node, cuems-reshape-devices
```

⚠ **Do not reach for `python -m cuemsutils.xml.reshape_devices`.** That module has **no
`if __name__ == "__main__":` guard**, so `-m` does nothing at all and **exits 0** — a silent
no-op reporting success, which is precisely the defect class this feature exists to remove.
(`convert_documents` does have the guard, so `-m` works there; use the console script for both
anyway, so there is one idiom and not two.)

**`cuems-convert-documents` takes FILES, not a directory.** A directory argument is reported
`skipped ([Errno 21] Is a directory)` and exits 1 — verified. There is no discovery mode:

```bash
find <dir> -name '*.xml' -print0 | xargs -0 "$UBIN/cuems-convert-documents"
```

It writes a `<file>.<YYYYmmddTHHMMSS>.bak` beside each document **before** rewriting a byte, a
backup failure is fatal for that document only, and it is idempotent — a second pass reports
`already current` and changes nothing. **Delete the `.bak` files before committing.**

🔴 **It also silently destroys every XML comment**, with no warning and exit 0 — measured 10
comments → 0 on `cuems-common`'s annotated example, which that gate *"nearly ran over unattended"*.
`cuems-reshape-devices` does the same; both write through stdlib `ElementTree`, which drops comment
nodes on parse. **Check before you convert**, every time:

```bash
grep -c '<!--' <file>      # non-zero -> hand-rewrite instead of converting
```

**If a document's comments are part of its value, hand-rewrite it** — that is what `cuems-common`
did for its annotated example and `cuems-nodeconf` for one dmx-latency comment it carried into a
reshaped `<player>` block.

Measured, so you know what you are *not* risking: **indentation and whitespace survive** (they are
text), and so does **`xsi:schemaLocation`**. An **unused** `xmlns:xsi` declaration is dropped, which
is harmless — it carries no information. **The one thing to protect is the comments.**

Expect three verdicts per file and read them: `converted`, `already current`, and
`skipped (root element names no bundled schema)`. **`already current` on a file you know carries
`True` is §4.2's case, not a success** — it means the document is marked `doc_version="2"` and needs
a hand-rewrite.

`cuems-reshape-devices` (013's device shape) is *not* symmetric with it: given paths it takes files,
given no paths it **discovers** a tree from `--conf`/`--library`. Its verdicts include
`not applicable` (nothing to reshape) and `old-shape`. Only T029 needs it, and §4.5 has the order.

## 4. Method — three arms, measured, not inferred

This is non-negotiable and it is why the gates exist. Record **all three**, with the exact pass/fail
counts:

| Arm | How | Why |
|---|---|---|
| **A — branch point** | your suite against `cuems-utils` at its pre-014 state | the "before". ⚠ **T028: this arm is unavailable** — `cuems-engine` is coupled to feature 012 from `c31734c` onward (`coerce_identity` does not exist before it), so design your comparison *before* a run goes red |
| **B — after the library change** | your suite against the 014 branch, **your tree untouched** | this is the one that shows the damage, and it is the number that justifies the work |
| **C — after conversion** | your suite against the 014 branch, your fixtures converted | this is the one that has to be green |

### Taking arm A — use a **worktree**, never a branch switch

⚠ **Corrected 2026-10-05, after `cuems-nodeconf`'s gate hit this for real** (its report §4):
`../cuems-utils` was found mid-measurement in a detached `HEAD` at a commit predating `0.1.0rc14`,
because a *second* sibling session was running its own gate against the same shared checkout and had
switched it. Nothing was wrong in either repository; the shared tree is simply not safe to move
while another session is measuring against it. An earlier draft of this prompt told you to switch
it, which is what created the race.

**So do not move `../cuems-utils` at all.** Make your own throwaway worktree at the branch point and
point your suite at that:

```bash
git -C ../cuems-utils status --porcelain          # must be empty; if not, STOP and report
git -C ../cuems-utils branch --show-current       # must be 014-xs-boolean-and-media-elements

# your own pre-014 copy, named after this repository so two sessions cannot collide
W=/tmp/cuems-utils-pre014-$(basename "$(git rev-parse --show-toplevel)")
git -C ../cuems-utils worktree add --detach "$W" 84705b9

# arm A: run your suite with cuemsutils resolved to "$W/src" instead of ../cuems-utils/src
#   poetry/pytest repos:  PYTHONPATH="$W/src" ...
#   hatch repos:          whatever your CLAUDE.md says, with the path overridden

git -C ../cuems-utils worktree remove --force "$W"   # when you are done with arm A
```

⚠ **`84705b9` is the branch point — do not substitute 013's tip.** `cuems-common`'s gate used
`c02f35c` instead, reasoning (correctly) that `main` sits 224 commits behind and would be a useless
baseline — but `c02f35c` is **013's landing commit**, and **14 commits separate it from the 014
branch point**. For that repository the two were equivalent: it imports no `cuemsutils` and none of
the 14 touches a schema. **For a repository that imports the library they are not**, because
`be3e86e` — the strict `_Bool.decode` — is among them, and `tasks.md` lists it as **S1, "Already
settled — do not redo"**, i.e. a *precondition* rather than part of 014's diff. An arm A at
`c02f35c` folds S1 into your measured delta and reports a change this feature did not make.
Verify with `git -C ../cuems-utils merge-base 014-xs-boolean-and-media-elements feat/xml-refactor`.

**Never commit in `../cuems-utils`, never check out a different commit in it, and never leave it on
a detached HEAD.** Arms B and C run against it as it stands, which is the whole point of not moving
it. Verify it is still on `014-xs-boolean-and-media-elements` and clean before you finish.

If the worktree cannot be created, say so and report arm A as **UNAVAILABLE — shared checkout in
use** rather than switching the branch anyway. An arm reported unavailable with the reason is a
result; an arm that silently measured the wrong library is worse than no arm.

### The rule three gates have now hit — a refusal fixture keeps its old form

⚠ **Do not convert a fixture whose purpose is to be refused.** It must keep the form it is refused
for, or the test passes for a new reason and stops testing anything. Three instances so far, and
nobody predicted any of them from outside the repository that owns them:

| Repository | Fixture | Exists to test |
|---|---|---|
| `cuems-editor` | `tests/fixtures/script_minimal.xml` | refusal for the **pre-013 device shape** |
| `cuems-power-bridge` | `tests/fixtures/network_map/map-incomplete/network_map.xml` | `NETWORK_MAP_INVALID` — a missing required `<mac>` |
| `cuems-power-bridge` | `tests/fixtures/network_map/map-pre007/network_map.xml` | `NETWORK_MAP_RETIRED_VOCABULARY` — an old `<node_type>` |

**`cuems-convert-documents` will refuse these for you** — it did in both power-bridge cases — but do
not rely on that: a document can be refusal-testing *and* convertible. **The check is "is this
document still refused for the reason it was written to test?", not "is it converted?"** Read the
test that consumes each fixture before you touch it, and say in your report which ones you left and
why. §4.1 of the migration guide enumerates the ones this repository could see from outside; your
repository's tests are the authority on the rest.

**If a failure is not a fixture, stop and report it.** That is a finding for feature 014 itself and
belongs back in `cuems-utils`, not worked around here. Every one of the ~96 failures 013 measured in
`cuems-engine` was a fixture; if yours is a source file, that is new information.

## 5. Your gate — find your repository below and do only that section

### If you are in `cuems-engine` — T028

**Six documents, all unmarked, the automatic kind:**

```
dev/network_map.xml
dev/test_xml_files/network_map.xml
dev/test_xml_files/script_one_cue_in_a_cuelist.xml
dev/test_xml_files/projects/complex_test/script.xml
dev/test_xml_files/projects/empty_test/script.xml
dev/test_xml_files/projects/fade_actions_v1/script.xml
```

⚠ **And a seventh that the tool will NOT fix** —
`dev/test_xml_files/projects/complex_test_v2/script.xml`. It is already `doc_version="2"`, so the
registry sees a current document and runs nothing (migration guide §4.2). `cuems-utils`' T015
claimed this file and did not rewrite it; verified still old-form 2026-10-05. **Hand-rewrite it**:
`True` → `true`, `False` → `false`, in those five elements only, nothing else in the file. Confirm
case-only, e.g. by asserting `new.lower() == old.lower()` for each substitution.

Also, from the migration guide §2.1: `MediaType` gained `pixel_width`, `pixel_height`, `file_size`
and `file_hash`, all optional. **An engine that ignores them is correct** — adopting them is your
decision, not this gate's. If you want the note: `file_hash` is a strictly stronger "was this file
replaced under the same name?" test than `file_size` against `os.stat`, and whether hashing a
multi-gigabyte file at arm time is acceptable is yours to judge.

### If you are in `cuems-power-bridge` — T029

**Ten documents, all unmarked:**

```
tests/fixtures/network_map/map-{no-self,controller-only,incomplete,mixed,pre007,
                               none-adopted,two-adopted,partial-resolve,
                               unresolvable,no-settings}/network_map.xml
```

⚠ **Expect arm B to be red before you start, and mostly for a reason that is not 014's.** Measured
2026-10-02 against this branch: **55 failed / 221 passed**, nearly all of it **013's old device
shape** (183 `pre-013 device shape` refusals). Its 276/276 green state predates 013. So:

**Reshape first, then convert — that order, or neither completes** (§4.5). Reshape-first sees a
version-1 `<duration>`; convert-first sees old-shape cues:

```bash
find tests/fixtures -name '*.xml' -print0 > /tmp/pb-docs
xargs -0 "$UBIN/cuems-reshape-devices"   < /tmp/pb-docs
xargs -0 "$UBIN/cuems-convert-documents" < /tmp/pb-docs
```

**Separate the two causes in your report.** "55 failed" is not a 014 result; "N failed *after*
reshape, attributable to the boolean" is. If reshape refuses a document because it would not
validate, that is T034's specified behaviour in 013 — report the document, do not force it.

### If you are in `cuems-nodeconf` — T030

**One document**: `tests/fixtures/etc_cuems/network_map.xml`. Also check
`tests/fixtures/etc_cuems/settings_sentinel.xml` per 013's table — `settings` declares no boolean,
so expect it to need nothing, and **say so** rather than leaving it unchecked.

⚠ **You are the only repository whose *output* this feature changes.** You rewrite
`/etc/cuems/network_map.xml` every 30 s. So the gate is not only fixtures:

1. Confirm your **write path emits `true`/`false`** after the library moves. Assert the **bytes**,
   not the object — a test on the object cannot catch a writer that bypasses `Mapper._lexical`.
2. Understand the one-way door you own (migration guide §4.3): `CuemsNetworkMapType.save()` bumps
   `doc_version`, after which an **older** `cuems-utils` refuses the map with `DocumentTooNewError`.
   So on a node the package must be upgraded **before** nodeconf restarts, and there is **no
   rollback** afterwards. If your own docs describe an upgrade or rollback procedure, it needs this.

**Two documentation corrections**, because they now teach a refused spelling:
`CLAUDE.md` and `specs/001-network-map-object-adoption/quickstart.md` both show `<adopted>True</…>`.

### If you are in `cuems-common` — T031

**Three documents, not two** — the count in older notes is wrong:

```
tests/fixtures/maps/converted.xml
tests/fixtures/maps/unconverted.xml
etc/cuems/network_map.xml.example          # ⚠ the one a *.xml glob misses
```

⚠ **The example is the one that breaks a test.**
`tests/test_documented_validation.py::test_documented_command_accepts_valid_maps[example]` validates
it **directly against `../cuems-utils/.../schemas/network_map.xsd` with no version conversion** — a
raw `XMLSchema11` validate in a subprocess — so `True` is now simply invalid there. No conversion
runs on that path to rescue it.

⚠ **Two test modules carry inline XML literals** a path list does not reach:
`tests/test_controller_resolution.py` and `tests/test_network_map_conversion.py`. Same treatment as
`cuems-utils`' T015a, which fixed 16 such literals across 7 modules. **In
`test_network_map_conversion.py` the literals are the input *and* the expected output of
`cuems-migrate-network-map`**, which rewrites `node_type` → `node_role` only and never touches a
boolean — so convert **both sides or neither**, or the test starts failing for a newly wrong reason.

⚠ **Do not go looking for a mirrored XSD to update.** Older notes say this repository mirrors the
six schemas and ships `network_map.xml`; feature 011 transferred custody to `cuems-utils`, and
`debian/postinst:173` now copies `cuems-utils`' own
`/usr/share/cuems/schemas/network_map.xsd` → `/etc/cuems/`. There is **no stale mirror**. Verify
that rather than taking it from me, and if you find one, that *is* the finding.

Do check that `debian/postinst`'s `cuems-migrate-network-map` step still leaves a live map the new
library accepts. It should: the map is unmarked, so the registry converts it on read.

### If you are in `cuems-editor` — T032

**Three of four documents convert:**

```
tests/fixtures/conf/network_map.xml
tests/fixtures/script_minimal_013.xml
specs/001-cuems-utils-migration/evidence/mappings-capture/network_map.xml
```

⚠ **`tests/fixtures/script_minimal.xml` is the fourth and must stay old-form.** Your own
`tests/fixtures/README.md` records why, and it pins its hash: it is **pre-013 device shape** and the
source of the pre-migration `project` capture under
`specs/001-cuems-utils-migration/evidence/project-capture/`. The library already refuses to load it,
by design. It is also `tests/conftest.py`'s `FIXTURE_XML`, which is why four of the five arm-B
failures are in `test_project_payload.py` — they run against a document that is *meant* to be
refused.

So this gate is **not** "convert everything" — it is *"convert the three and confirm the fourth is
still refused, **for the right reason**"*. Check the reason, not just the refusal: before this
feature it was refused for its device shape, and a boolean failure masking that would look identical
from the outside while testing something else. `script_minimal_013.xml` is the reshaped copy and
**does** convert (its README row says it carries no `doc_version`, so the library converts it 1 → 2
in memory on load).

**Expected arm B, measured 2026-10-05**: `5 failed / 149 passed / 2 skipped / 1 xfailed`. The five
are `test_node_merge.py::test_merged_nodes_carry_the_string_wire_form` and four in
`test_project_payload.py`. The first is a **retired premise**, not breakage — the wire form is no
longer a string, which is the whole of this feature — so invert or narrow it **in place, with what
replaces it**, and do not delete it. That is the discipline `cuems-utils`' T017 applied to twenty
modules.

**And close your own T059**, which is a second, separate job in the same session.
`tests/test_schema_descriptor.py::test_config_save_of_settings_persists_through_save_settings` is
`xfail(strict=True)`. An upstream note said it would turn XPASS by re-run; **that was measured and
is false** — see migration guide §3.1. `CuemsWsUser.config_save` calls `notify_error_to_user`
**unconditionally** for all four configuration domains, so no library change can satisfy it. The
library half is now complete:

```python
manager  = ConfigManager(load_all=False)
document = manager.from_json(SchemaName.SETTINGS, payload)   # new in 014
document.save(manager.conf_path('settings.xml'))
```

Three things to know before you write it:

- **`from_json` returns the object; there is no installer, by decision.** `save_settings` writes
  what a `ConfigManager` *holds*, and two of the four domains hold it on a private attribute. The
  root object's own `save(path)` is the same body all four `save_*` delegate to.
- **The payload your test sends is one level deeper than the document.** `manager.to_wire('settings')`
  projects the root's `Settings` *field*, not the root — `Settings.main_key` is `'Settings'`. That
  exact shape is accepted; `cuems-utils` pins it in
  `tests/integration/test_config_ingestion.py::test_from_json_ingests_this_librarys_own_settings_projection`.
- **Keep your refusals.** `script` and `hardware_outputs` stay in `CONFIG_SAVE_REFUSED`;
  `from_json` refuses them too, with the same reasons. Do not widen them.

Remove the `xfail` marker once it passes — a strict xfail that passes is an error, so leaving it is
not a neutral choice. And correct `src/cuemseditor/CuemsWsServer.py:435`, whose docstring still
documents `"True"`/`"False"` as the wire form for `adopted` and `online`.

## 6. What to report back

End your session with this, so `cuems-utils`' T033 can record it without re-deriving anything:

```
REPOSITORY: <name>            GATE: T0NN        HEAD: <sha>
LIBRARY:    ../cuems-utils @ <branch> <sha>

ARM A (branch point):   <n passed / n failed / n skipped>   or  UNAVAILABLE — <why>
ARM B (library moved):  <n passed / n failed / n skipped>
ARM C (converted):      <n passed / n failed / n skipped>

DOCUMENTS CONVERTED:    <path> ... (and by which route: tool / hand-rewritten / left old-form)
SOURCE CHANGED:         <paths, or "none">
TESTS WHOSE PREMISE WAS RETIRED: <path::name — what replaced it>

STILL RED:              <test — and WHY, attributed to 014 / 013 / pre-existing>
FINDINGS FOR cuems-utils: <anything that is not a fixture, or "none">
COMMITS:                <sha — subject>
```

**A sibling left red with the reason named is a result. A sibling not run is not.** Record an arm
that is red rather than restating it as passing, and attribute each remaining failure to 014, to
013, or to something that predates both.

## 7. Guardrails

- **Do not edit `../cuems-utils`.** Not the schemas, not the tests, not the specs. If something
  there is wrong, report it under `FINDINGS FOR cuems-utils`.
- **Do not edit another sibling.** One repository per session is the point.
- **Do not touch** `cuems-engine/specs/008-*/evidence/baseline-suite*.txt` or
  `cuems-editor/specs/001-*/evidence/suite-after-import.txt`. They are **captured test output** in
  landed feature directories — a record of what a run said on a day. Rewriting them falsifies
  evidence.
- **Do not regenerate a golden to make a test pass.** FR-021 binds here too. A golden moves only
  when the change to it *is* the deliverable, and then it moves in the same commit as the reason.
- **Do not bump any version or dependency bound.** `0.1.0rc16` does not move and nothing ships from
  this work alone — everything waits for the coordinated `xml-refactor-merge-candidate` tag after
  features 011–015.
- **Do not create or move a tag.** Moving a published tag is maintainer-only, never an agent's.
- Follow **this** repository's commit conventions, including GPG signing where its `CLAUDE.md` says
  so. Retry on "gpg failed to sign"; never pass `--no-gpg-sign`.
- Clean up: delete the `*.bak` files the conversion tool leaves, and return `../cuems-utils` to
  `014-xs-boolean-and-media-elements` if you moved it.

<<< END — copy to here

---

## Maintainer notes (not part of the prompt)

**Why the prompt makes each session re-verify what it is told.** Three of the facts it carries were
wrong in `tasks.md` until 2026-10-05, and each was found by checking rather than by reading:
`cuems-common` has three affected documents and not two; it has no mirrored XSD to update; and
`cuems-convert-documents` takes files and not directories, which every earlier draft of the release
note got wrong. So the prompt says "verify that rather than taking it from me" where it can, and the
report-back block asks for measurements rather than confirmations.

**Why T028's hand-rewrite is in the prompt rather than done here.** It is a sibling file. `T015`
claimed it, missed it, and `T028` was written to "verify the result in place" — so the correction is
that T028 must *rewrite* it. Doing it from `cuems-utils` would repeat the mistake of one repository
reaching into another's tree, which is the thing the gate split exists to stop.

**Expected arm B figures, so a session can tell a surprise from the forecast** — measured
2026-10-02 (power-bridge) and 2026-10-05 (editor), both against this branch:

| Repository | Arm B | Attributable to 014 | Dominant cause |
|---|---|---|---|
| `cuems-editor` | **5 failed / 149 passed — confirmed exactly** | 5 | 1 retired premise + 4 payload |
| `cuems-nodeconf` | **33 failed / 141 passed** | **1** | **32 are 013's device shape**, identical in arm A |
| `cuems-power-bridge` | **55 failed / 221 passed** | **0** | **all 55 are 013's**, arms A and B diffed identical |
| `cuems-common` | **102 / 104** | 2 | both on the `.xml.example` validated raw — **exactly as forecast, and nothing else** |
| `cuems-engine` | **70 failed / 827 passed / 26 errors** | **0** | **all 96 are 013's device shape**, attributed by error type because arm A was unavailable |

A session that measures a figure far from these should say so — it means something moved between
2026-10-02 and its run, and that is worth more than the gate itself.

⚠ **The pattern across the four landed rows is the thing to expect**: in two of four, most of
arm B was **not 014** — and in `cuems-power-bridge`, *none* of it was. **Arm A is what separates
them**, which is why it is worth the worktree: without it that repository would have reported 55
failures against this feature and every one would have been someone else's.

**Two findings came back from gates rather than from this repository's own work**, so expect your
session to produce one too and leave room for it:
`cuems-nodeconf` found that 013's reshape defeats F3's `settings` conversion
(`settings-reshape-defeats-f3-conversion-defect.md` — it blocks the tag, and
`cuems-power-bridge` then hit it 9 times out of 9), and `cuems-editor` found that
`conf_path`/`project_path` refuse the file a first save would create (UR-6). Neither was visible
from inside `cuems-utils`.

⚠ **013's sibling migration was never completed, and the 014 gates are paying for it.** Two gates
have now hand-rewritten 11 `settings.xml` between them because
`specs/013-device-class-reshape/sibling-repository-updates.md` left the siblings as *"a prediction
for them"* and nobody closed it. **If your repository has `settings.xml` fixtures, check them for
the pre-013 shape before you start**, and report that work separately from 014's — both landed
gates did, which is why the attribution above is possible at all.
