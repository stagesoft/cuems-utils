"""Root key order survives decode → encode — contract C3, FR-005 (T012b).

**This test passes on pre-005 code**, and it is written *before* the tasks that
could break it (T024/T025) for exactly that reason.

``CuemsScript`` is an ``xs:all`` type. The schema states that no order is
imposed on its children, so ``TypeSpec.order_keys`` returns them as given and
**emission order is arrival order**. Meanwhile ``ensure_items`` — the
programmatic construction path — sorts keys alphabetically.

Route decode through the sorting constructor and every hand-authored script's
root element is rewritten on the next save. That is the single most dangerous
change available in this feature, and two of the four captured ``CuemsScript``
roots are *not* alphabetical, so it is not hypothetical.

``test_byte_identity_xml.py`` covers this in aggregate. It is worth pinning
directly as well: a 24 KB byte diff tells you a document changed, while a key
list tells you *the root was re-sorted*, which is a different bug report.
"""

from __future__ import annotations

import json

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT, by_relpath

#: Hand-authored, and deliberately **not** alphabetical: ``description`` before
#: ``created`` before ``modified``, with ``CueList`` last. Sorting would give
#: ``CueList, created, description, id, modified, name, ui_properties``.
HAND_AUTHORED = "cuems-engine/projects/complex_test/script.xml"

OUTCOMES = json.loads((GOLDEN_ROOT / "outcomes.json").read_text())

#: Script documents that actually reach the object layer. Scoped by the
#: **pinned outcome** rather than by category: two ``cuems-engine`` scripts
#: declare a namespace the schema does not load and are pinned as read
#: failures, and whether they read is ``test_accept_reject_parity``'s question,
#: not this file's. Deriving the list from ``outcomes.json`` also means a
#: document that starts or stops decoding fails *there*, where the parity
#: obligation lives, rather than showing up here as a confusing ordering error.
SCRIPT_DOCS = [
    d
    for d in DOCUMENTS
    if d.schema == "script"
    and OUTCOMES.get(d.relpath, {}).get("read", {}).get("ok") is True
    and OUTCOMES.get(d.relpath, {}).get("to_objects", {}).get("ok") is True
]
IDS = [d.relpath for d in SCRIPT_DOCS]


def root_keys(obj) -> list[str]:
    """The root's key order as the writer will see it."""
    return list(dict.keys(obj))


def test_the_hand_authored_root_is_not_alphabetical():
    """The premise. If this ever fails, the test below proves nothing.

    A corpus whose roots all happened to be sorted would let the sorting bug
    ship green, so the property that makes this document load-bearing is
    asserted rather than assumed.
    """
    keys = root_keys(rt.read_objects(by_relpath(HAND_AUTHORED)))
    assert keys != sorted(keys), (
        f"{HAND_AUTHORED}'s root is alphabetical ({keys}), so it can no "
        f"longer detect a construction path that sorts"
    )


def test_the_hand_authored_root_keeps_its_exact_order():
    """Pinned as a list, so a failure names the cause."""
    assert root_keys(rt.read_objects(by_relpath(HAND_AUTHORED))) == [
        "id",
        "name",
        "description",
        "created",
        "modified",
        "ui_properties",
        "CueList",
    ]


def test_the_parametrisation_is_not_empty():
    """A list derived from pinned outcomes can shrink to nothing in silence."""
    assert len(SCRIPT_DOCS) >= 2


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_every_script_root_survives_decode_unchanged(doc):
    """Arrival order in, arrival order out, for every script in the corpus.

    Compared against the **document's** element order rather than against a
    stored expectation, so a new corpus document is covered the day it lands.
    """
    import re

    source = doc.path.read_text()
    body = re.search(r"<CuemsScript>(.*?)</CuemsScript>", source, re.S)
    if body is None:
        pytest.skip(f"{doc.relpath} has no CuemsScript body")

    # Immediate children only: the first tag opened at each point, in order.
    in_document: list[str] = []
    depth = 0
    for match in re.finditer(r"<(/?)([A-Za-z_][\w.-]*)[^>]*?(/?)>", body.group(1)):
        closing, tag, self_closing = match.groups()
        if closing:
            depth -= 1
            continue
        if depth == 0:
            in_document.append(tag)
        if not self_closing:
            depth += 1

    decoded = root_keys(rt.read_objects(doc))
    assert decoded == in_document, (
        f"{doc.relpath}: root key order changed.\n"
        f"  document: {in_document}\n"
        f"  decoded:  {decoded}"
    )
