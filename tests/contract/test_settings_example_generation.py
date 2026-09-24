# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""D15/D16/D17 — the generated ``settings.xml`` is a shippable artifact now.

`specs/planning/etc-cuems-first-install.md` D2 schedules
``generate_settings_example()``'s output to be produced at package build and
installed on every node. That promotion changes what the values behind it are:
a table documented as *illustrative* becomes the configuration a fresh machine
starts life with, and a placeholder nobody checked becomes a placeholder
everybody runs.

This file is the check that came with the promotion. Three defects were fixed
together because the correction is what makes the last two matter:

**D15 — the values were wrong, and wrong invisibly.** All four player sections
named ``/usr/bin/cuems-player``, a binary **absent from both audited production
machines and never shipped by any package**. The audit corrected each entry by
*consumption* — who actually reads the field — rather than by transcribing a
machine, since both hosts predate this refactor.

**D16-A — one of the four sections was generated from the wrong type.** The
mixer passed ``"PlayerType"`` as both lookup name and ``TypeKey`` while holding
the ``AudioMixerType`` model, and got away with it because that extension is
currently empty. The cost was not a wrong document today; it was that FR-034's
generation-time completeness guarantee had a **hole at one of four sections** —
proven by patching the schema: a new required field on ``DmxPlayerType`` raised
the documented ``RuntimeError`` naming the table, while the same field on
``AudioMixerType`` produced silence and then a ``SchemaError`` naming neither.

**D16-B — a base-class fallback answered for fields nobody declared.** That is
*how* one wrong path reached four sections while looking deliberate in each.

**D17 — the optional knobs were unreachable.** The generator filtered to
``f.required``, so ``osc_port`` and the three ``output_latency_ms`` entries
could never be emitted and their table entries were dead by construction.

The tests below are written against the **contract**, not the current strings,
wherever that is possible: the point is not that ``path`` says
``cuems-videocomposer`` today, it is that a section can never again inherit a
value it did not declare.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import (
    _SETTINGS_EXAMPLE_VALUES,
    _settings_example_value,
    generate_settings_example,
)
from cuemsutils.xml.spec import FieldKind, TypeKey, derive

#: The four concrete player types, and the element each is reached by.
PLAYER_SECTIONS = {
    "videoplayer": "VideoPlayerType",
    "audioplayer": "AudioPlayerType",
    "audiomixer": "AudioMixerType",
    "dmxplayer": "DmxPlayerType",
}

#: The abstract base. No element uses it (``settings.xsd`` declares it only as
#: the ``xs:extension`` base of the four above), so it must never appear as a
#: values-table key or as a generator lookup name.
ABSTRACT_BASE = "PlayerType"


def _scalar_fields(type_name: str) -> tuple[str, ...]:
    """Every scalar field the type declares, required **and** optional."""
    return tuple(
        f.name
        for f in derive(TypeKey("settings", type_name)).fields
        if f.kind is FieldKind.ELEMENT and f.child is None
    )


# ---------------------------------------------------------------------------
# D16 — every section answers for itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", sorted(PLAYER_SECTIONS.values()))
def test_every_player_type_declares_all_of_its_own_values(type_name):
    """D16-A and D16-B at once, stated as the property rather than the fix.

    ``derive()`` flattens ``xs:extension``, so each concrete type's field list
    already includes the base's ``path``/``args``. The requirement is that the
    **table** does not flatten: every field must be answered under the concrete
    type's own name.

    This is what closes D16-A's hole. A required field added to
    ``AudioMixerType`` — the case that used to pass in silence — fails here,
    naming the type and the field, at the commit that adds it.
    """
    missing = [
        field
        for field in _scalar_fields(type_name)
        if (type_name, field) not in _SETTINGS_EXAMPLE_VALUES
    ]
    assert not missing, (
        f"{type_name} declares {missing} with no entry under its own name in "
        "_SETTINGS_EXAMPLE_VALUES. There is no base-class fallback any more "
        "(D16-B) -- add the entry under the concrete type."
    )


def test_the_abstract_base_is_not_a_values_key():
    """D16-B, pinned at the table rather than at the lookup.

    A single ``("PlayerType", "path")`` entry is all it takes to re-create the
    defect: four sections silently sharing one value, each looking deliberate.
    """
    base_keys = sorted(k for k in _SETTINGS_EXAMPLE_VALUES if k[0] == ABSTRACT_BASE)
    assert not base_keys, (
        f"{base_keys} would be reachable by no element and answer for every "
        "player subtype at once -- which is how /usr/bin/cuems-player, a binary "
        "that never existed, reached all four sections."
    )


def test_the_fallback_is_gone():
    """The lookup half: an unknown field raises instead of borrowing a value."""
    with pytest.raises(RuntimeError, match=r"has no example value"):
        _settings_example_value(ABSTRACT_BASE, "path")


def test_the_error_names_the_table_and_the_fix():
    """FR-034 rests on this message being actionable.

    The guarantee is not "it fails" — a ``SchemaError`` three layers later also
    fails. It is that the failure says which field, which table, and what to do.
    """
    with pytest.raises(RuntimeError) as raised:
        _settings_example_value("DmxPlayerType", "no_such_field")
    message = str(raised.value)
    assert "DmxPlayerType.no_such_field" in message
    assert "_SETTINGS_EXAMPLE_VALUES" in message
    assert "add one" in message


# ---------------------------------------------------------------------------
# D15 — the values themselves
# ---------------------------------------------------------------------------


def test_the_four_player_paths_are_distinct():
    """The shape of the D15 defect, independent of the strings that fixed it.

    Four sections sharing one path is not a coincidence a reviewer would catch
    by reading four plausible-looking lines; it is the observable signature of
    a fallback. Asserting distinctness catches a regression that asserting the
    four literals would also catch — and keeps catching it after someone
    legitimately renames a binary.
    """
    paths = {name: _settings_example_value(name, "path") for name in PLAYER_SECTIONS.values()}
    assert len(set(paths.values())) == len(paths), paths


def test_no_value_names_the_binary_that_never_existed():
    """Named explicitly because it survived years of review.

    It was absent from both audited machines and shipped by no package, yet it
    read as intentional in four places.
    """
    assert "/usr/bin/cuems-player" not in set(_SETTINGS_EXAMPLE_VALUES.values())


def test_the_editor_url_is_the_brand_hostname():
    """D15: CUEMS is the internal machinery; formitgo is what an operator types.

    Pinned because it is the one corrected value a future reader is most likely
    to "fix" back toward the implementation's own name.
    """
    assert _settings_example_value("SettingsType", "editor_url") == "formitgo.local"


# ---------------------------------------------------------------------------
# D17 — optional fields are emitted
# ---------------------------------------------------------------------------


def _node(document):
    return document["Settings"]["node"]


@pytest.mark.parametrize(
    "section,field",
    [
        ("videoplayer", "osc_port"),
        ("videoplayer", "output_latency_ms"),
        ("audioplayer", "output_latency_ms"),
        ("dmxplayer", "output_latency_ms"),
    ],
)
def test_optional_player_fields_are_emitted(section, field):
    """The four fields that were unreachable by construction.

    Production split on exactly these: one audited host omits them, the other
    writes them out, and the two behave identically because the engine treats
    absent and ``"auto"`` alike. The tie is broken toward the operator being
    able to *see* the knob.
    """
    assert field in _node(generate_settings_example())[section]


def test_every_declared_player_field_is_emitted():
    """The general statement of the four cases above.

    A fifth optional field added to a player section is covered without editing
    this file, which is the difference between a test and a list.
    """
    document = generate_settings_example()
    for section, type_name in sorted(PLAYER_SECTIONS.items()):
        emitted = set(_node(document)[section])
        missing = sorted(set(_scalar_fields(type_name)) - emitted)
        assert not missing, f"{section} omits {missing}"


def test_the_generated_document_is_schema_valid(tmp_path):
    """The whole point, measured end to end.

    Widening past ``f.required`` and re-keying the mixer both change what is
    written; ``save()`` runs T1, so a document that stopped validating fails
    here rather than on a node.
    """
    target = tmp_path / "settings.xml"
    generate_settings_example().save(target)
    assert target.exists() and target.stat().st_size > 0


def test_the_identity_stays_the_reserved_sentinel():
    """D3 — the *shipped* document is never specialized.

    The generator must stay deterministic (D2: a fresh uuid4 at build time
    would make the package non-reproducible) and the sentinel is what
    ``cuems-init-node`` looks for to know a node is unprovisioned. Minting here
    would silently give every machine imaged from one package the same "real"
    identity — practice 7's placeholder collision, but harder to see.
    """
    node = _node(generate_settings_example())
    assert node["uuid"] == "00000000-0000-0000-0000-000000000000"
    assert node["mac"] == "000000000000"
