# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T007 — the token scanner (feature 012, FR-002, FR-009).

The scanner's one non-obvious output is ``embedded``, and every case below is a
form measured in a real document: a bare ``<uuid>``, the compound
``<identity>_<output>`` in a script's ``<output_name>`` (research R12), the
``<identity>_custom_<n>`` variant, and the three ``default_*_output`` elements
in the mappings, which carry the same compound form.
"""

from __future__ import annotations

from cuemsutils.tools import ids

UUID1 = "0367f391-ebf4-11b2-9f26-000000000001"
UUID4 = "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"


def test_a_bare_element_value_is_not_embedded():
    found = ids.scan_text(f"<node><uuid>{UUID1}</uuid></node>")
    assert len(found) == 1
    assert found[0].value == UUID1
    assert found[0].element == "uuid"
    assert found[0].embedded is False
    assert found[0].context == UUID1
    assert found[0].classification == ids.NOT_CONVERGED


def test_surrounding_whitespace_still_counts_as_the_whole_value():
    """Pretty-printed documents are the common case in this corpus, and a
    scanner that called an indented value "embedded" would report every
    hand-authored document as full of compound strings."""
    found = ids.scan_text(f"<uuid>\n    {UUID4}\n  </uuid>")
    assert len(found) == 1 and found[0].embedded is False


def test_the_compound_output_form_is_embedded():
    found = ids.scan_text(f"<output_name>{UUID1}_0</output_name>")
    assert len(found) == 1
    assert found[0].element == "output_name"
    assert found[0].embedded is True
    assert found[0].context == f"{UUID1}_0"


def test_the_custom_output_form_is_embedded():
    found = ids.scan_text(f"<output_name>{UUID1}_custom_3</output_name>")
    assert len(found) == 1 and found[0].embedded is True
    assert found[0].context.endswith("_custom_3")


def test_the_three_default_output_forms_are_each_found_and_embedded():
    text = (
        f"<default_audio_output>{UUID1}_1</default_audio_output>"
        f"<default_video_output>{UUID1}_0</default_video_output>"
        f"<default_dmx_output>{UUID1}_2</default_dmx_output>"
    )
    found = ids.scan_text(text)
    assert [f.element for f in found] == [
        "default_audio_output",
        "default_video_output",
        "default_dmx_output",
    ]
    assert all(f.embedded for f in found)


def test_a_file_with_no_tokens_yields_nothing():
    assert ids.scan_text("<Settings><library_path>/opt/cuems_library</library_path></Settings>") == []
    assert ids.scan_text("") == []


def test_offsets_are_where_the_token_actually_starts():
    """The offset is what a literal substitution would act on, so it has to be
    the token's own position and not the element's."""
    text = f"<a><uuid>{UUID1}</uuid></a>"
    found = ids.scan_text(text)
    assert text[found[0].offset:found[0].offset + 36] == UUID1


def test_every_token_in_a_document_is_found_in_order():
    text = (
        f"<node><uuid>{UUID1}</uuid></node>"
        f"<output_name>{UUID4}_0</output_name>"
        f"<id>{UUID4}</id>"
    )
    found = ids.scan_text(text)
    assert [f.value for f in found] == [UUID1, UUID4, UUID4]
    assert [f.embedded for f in found] == [False, True, False]


def test_a_token_outside_any_element_reports_no_element():
    """Reported rather than guessed: an attribute value or a token in a file
    that is not XML at all has no enclosing element, and inventing one would
    put a wrong location in an operator's report."""
    found = ids.scan_text(UUID1)
    assert len(found) == 1 and found[0].element is None


def test_the_scanner_runs_on_text_no_parser_would_accept():
    """The property every caller depends on (FR-006a): after the narrowing,
    every document the re-mint repairs is one the schema refuses, and some are
    not even well-formed."""
    found = ids.scan_text(f"<node><uuid>{UUID1}</uuid><unclosed>")
    assert [f.value for f in found] == [UUID1]


def test_scan_file_reads_a_file(tmp_path):
    path = tmp_path / "mappings.xml"
    path.write_text(f"<nodes><node><uuid>{UUID1}</uuid></node></nodes>", encoding="utf-8")
    found = ids.scan_file(path)
    assert [f.value for f in found] == [UUID1] and found[0].embedded is False
