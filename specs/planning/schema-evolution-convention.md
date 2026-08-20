# Schema evolution convention

**Adopted**: 2026-08-20, by feature `006-public-object-api` (T081, T082)
**Applies to**: every `.xsd` under `src/cuemsutils/xml/schemas/`
**Status**: binding on all CUEMS repositories that read or write those documents

## Why this exists

A CUEMS deployment has show files, settings files, mappings files and network
maps sitting on nodes, written months ago by versions of the software nobody is
running any more. Those files are the installation. A schema change that
invalidates them does not produce a compile error or a failing test — it
produces a node that will not start, at a venue, on the day of a show.

That is not hypothetical. It has already happened once, and the two artifacts it
broke are vendored in this repository as evidence. See **X13** below.

---

## The four rules

### 1. An element added to an existing complex type is **optional**

`minOccurs="0"`. Always, without exception, regardless of how obviously required
the new element feels.

A required element added to a type that documents already use makes every one of
those documents invalid the moment the new schema ships. There is no version
negotiation in this system: the node reads the file with whatever schema the
installed package carries.

```xml
<!-- yes -->
<xs:element name="gradient_osc_port" type="cms:NonPrivilegedPort" minOccurs="0" />

<!-- no -->
<xs:element name="gradient_osc_port" type="cms:NonPrivilegedPort" />
```

### 2. It carries a **model-layer default**, so an omitting document loads to the same object

Optional in the schema is only half of it. A document that omits the element must
decode to an object indistinguishable from one that carries the element's
default — otherwise every consumer grows a `if 'x' in conf:` branch, and the
"optional" element becomes a permanent two-shape problem.

The default belongs in the model class's `DECLARED_DEFAULTS`, next to the field:

```python
class NodeConfType(ConfigDict):
    DECLARED_DEFAULTS = {
        ...
        "gradient_osc_port": 7100,   # not Unset — an omitting document gets this
    }
```

Use `Unset` only when the field genuinely has **no** meaningful default and
absence is the correct decoded state — an optional `canvas_region`, for example,
whose presence is what distinguishes an output's two modes.

### 3. Required elements appear only in **new** types

A type no document has ever contained cannot invalidate a document. So when a
change genuinely needs required fields, introduce the type rather than extending
one in use, and reference it with `minOccurs="0"` from wherever it attaches.

### 4. Anything else is a **versioned file-format migration**, with a conversion path

Renaming an element, changing a type in a narrowing direction, restructuring a
nesting, removing an element consumers read — none of these are schema edits.
They are file-format changes, and they need:

- a version marker that lets a reader tell old from new;
- a conversion that runs on read, or a documented tool that runs once;
- a release note naming what has to be converted and when the old form stops
  being accepted.

"We will just update the files on the nodes" is not a conversion path. Nobody
knows where all the files are.

---

## The precedent: X13

`gradient_osc_port` was added to `settings.xsd` inside `NodeConfType` — an
existing type, present in every settings file ever written — **as a required
element**:

```xml
<xs:element name="gradient_osc_port" type="cms:NonPrivilegedPort" />
```

Every settings file written before that commit became invalid. Two of them are
this project's own, vendored under `tests/data/corpus/negative/`:

- `settings-utils-v0.1.0rc2.xml`
- `settings-utils-v0.1.0rc7.xml`

They are in the **negative** corpus tier — the tier for documents that must keep
*failing* — which is an uncomfortable place for two files the project itself
shipped as valid.

The failure mode is worth reading in full, because it is what rules 1 and 2
prevent:

```
Reason: Unexpected child with tag 'videoplayer' at position 13.
        Tag 'gradient_osc_port' expected.
```

That message names the *wrong element*. `xs:sequence` reports the first child it
did not expect, so an operator sees a complaint about `videoplayer` — an element
that is present, correct, and unchanged — and has to work backwards to a missing
one. A node with this settings file does not start, and the error points at the
wrong line.

Feature 006 made this legible rather than fixing it: `ConfigManager` raises
`SchemaError` naming `gradient_osc_port`, distinct from the `OSError` a *missing*
file raises (FR-014b, `tests/contract/test_config_errors.py`). An operator can
now tell "this file predates a schema change" from "there is no file".

### The violation is scheduled work, not resolved work (T082)

**No `.xsd` file is edited by feature 006** (FR-033). The convention is adopted
and the violation is recorded; correcting it is a separate change, and it needs
a decision this feature is not the right place to make.

What correcting it involves, so the next person does not have to rediscover it:

| Step | Note |
|---|---|
| Make the element `minOccurs="0"` | Rule 1. Cannot break anything: every valid document stays valid |
| Give `NodeConfType.gradient_osc_port` a model default | Rule 2. The value is `7100` in every shipped settings file, which is what makes it safe to default rather than a guess |
| Move the two vendored files out of the `negative` tier | They stop being negative fixtures and become ordinary ones — which is the observable evidence the fix worked |
| Update `tests/golden/outcomes.json` for those two | A **third** deliberate golden change beyond T065/T080, so it needs its own justification recorded, per standing rule 1 |
| Check `cuems-gradient-motiond` still gets a port | The element exists because that component needs one. Defaulting it must not silently point two components at the same port |

The last row is why this is not a five-minute change and why it is not being
made here.

---

## How this is enforced

It is not, mechanically, and saying so is better than implying otherwise.

There is no linter for "this element is required and its type is in use". What
exists is:

- this document, which a schema change is expected to be read against;
- the `negative` corpus tier, which makes a document broken by a schema change
  into a *vendored artifact* rather than a bug report from a venue;
- `tests/unit/test_coherence.py`, which fails when a schema type and its model
  class disagree about their field set — so an element added to the XSD and not
  to the model is caught immediately, and rule 2 cannot be forgotten silently
  even though rule 1 can.

The realistic protection is that adding a required element to an existing type
now has a name, a precedent, and a paragraph explaining what it costs.
