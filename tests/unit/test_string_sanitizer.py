"""``tools.StringSanitizer`` — untested despite being live in ``cuems-editor``
on a security-adjacent path (user-supplied strings become filesystem path
components and DB column values).

Real consumers, and what each expects (``StringSanitizer`` methods are all
``@staticmethod``, called unbound):

- ``CuemsUpload.set_upload``: ``sanitize_file_name(file_info['name'])`` on a
  client-supplied WebSocket upload filename, immediately used to build a
  filesystem path (``self.tmp_filename = self.filename + '.tmp' + ...``).
- ``CuemsDBProject.new``: ``sanitize_dir_permit_increment(unix_name)`` on a
  frontend-supplied directory name candidate, used verbatim in ``os.mkdir``.
- ``CuemsDBProject.new``/``CuemsDBMedia.update``:
  ``sanitize_name(data['CuemsScript']['name'])`` /
  ``sanitize_text_size(data['CuemsScript']['description'])`` feeding
  ``Project.name`` / ``Project.description`` — peewee ``CharField`` columns.
  ``CuemsDBModel.py``'s ``Project``/``Media`` both declare ``name =
  CharField(unique=True)`` with peewee's **default `max_length=255`** (peewee
  3.17's ``CharField.__init__``) — the real, enforced constraint
  ``sanitize_name``'s ``255`` is meant to respect, not an arbitrary number
  invented by this test.
- ``sanitize_dir_name`` has no consumer anywhere in the ecosystem as of this
  writing (checked across ``cuems-editor``, ``cuems-nodeconf``,
  ``cuems-engine``, ``cuems-common``) but is public API sharing the same
  truncate-then-clean shape as ``sanitize_file_name``; tested for parity.

## The off-by-one fix

``sanitize_name``/``sanitize_text_size`` truncated to one character short of
their own stated limit (``_string[0:254]``/``_string[0:65534]`` under comments
claiming "first 255"/"first 65535" characters) — confirmed as a real
discrepancy, not a deliberate safety margin, because peewee's actual
``CharField`` default is ``max_length=255`` exactly, and nothing downstream
relies on the truncated length being 254 rather than 255 (grepped: no
consumer inspects ``len()`` of a sanitized name/description). Fixed in the
same change as these tests, per the correction in
``specs/planning/tools-external-consumers-and-timeoutloop-migration.md``: real
testing confirmed the inaccuracy, so the source was corrected to match its own
documented intent rather than the test being written to pin the bug.

``sanitize_file_name``/``sanitize_dir_name``/``sanitize_dir_permit_increment``'s
240-character cap (``_string[0:236] + _string[-4:]``) has **no** such bug —
236 + 4 = 240, matching its own comment ("240 of max 255") — and is left
untouched.
"""

from __future__ import annotations

from cuemsutils.tools.StringSanitizer import StringSanitizer


# --- sanitize_name: Project.name / Media.name, peewee CharField(max_length=255) --


def test_sanitize_name_passes_short_strings_through_unchanged():
    assert StringSanitizer.sanitize_name("My Project") == "My Project"


def test_sanitize_name_passes_exactly_255_chars_through_unchanged():
    s = "a" * 255
    assert StringSanitizer.sanitize_name(s) == s


def test_sanitize_name_truncates_to_exactly_255_chars():
    """Matches peewee's ``CharField`` default ``max_length=255`` — the real
    constraint ``Project.name``/``Media.name`` enforce."""
    s = "a" * 300
    result = StringSanitizer.sanitize_name(s)
    assert len(result) == 255
    assert result == "a" * 255


# --- sanitize_text_size: Project.description / Media.description -------------


def test_sanitize_text_size_passes_short_strings_through_unchanged():
    assert StringSanitizer.sanitize_text_size("a short description") == "a short description"


def test_sanitize_text_size_passes_none_through_unchanged():
    # `if _string and (...)` — falsy input short-circuits, matching
    # CuemsDBMedia.update's `description=StringSanitizer.sanitize_text_size(...)`
    # being fed a value that may be None from the incoming payload.
    assert StringSanitizer.sanitize_text_size(None) is None


def test_sanitize_text_size_passes_empty_string_through_unchanged():
    assert StringSanitizer.sanitize_text_size("") == ""


def test_sanitize_text_size_passes_exactly_65535_chars_through_unchanged():
    s = "a" * 65535
    assert StringSanitizer.sanitize_text_size(s) == s


def test_sanitize_text_size_truncates_to_exactly_65535_chars():
    s = "a" * 70000
    result = StringSanitizer.sanitize_text_size(s)
    assert len(result) == 65535
    assert result == "a" * 65535


# --- sanitize_file_name: CuemsUpload's client-supplied upload filename -------


def test_sanitize_file_name_replaces_spaces_and_hyphens_with_underscores():
    assert StringSanitizer.sanitize_file_name("My Song - Final Mix.wav") == "my_song___final_mix.wav"


def test_sanitize_file_name_strips_non_alnum_except_dot_and_underscore():
    assert StringSanitizer.sanitize_file_name("Track #1 (Live)!.mp3") == "track_1_live.mp3"


def test_sanitize_file_name_lowercases():
    assert StringSanitizer.sanitize_file_name("UPPER.WAV") == "upper.wav"


def test_sanitize_file_name_truncates_to_240_chars_preserving_the_tail():
    """236 leading chars + the last 4 chars (extension), matching the
    comment's own arithmetic ("240 of max 255") — no off-by-one here."""
    long_name = "x" * 300 + ".wav"
    result = StringSanitizer.sanitize_file_name(long_name)
    assert len(result) == 240
    assert result.endswith(".wav")
    assert result.startswith("x" * 236)


# --- sanitize_dir_name: no known consumer, tested for parity with file_name --


def test_sanitize_dir_name_also_strips_dots_unlike_sanitize_file_name():
    assert StringSanitizer.sanitize_dir_name("my.project.name") == "myprojectname"


def test_sanitize_dir_name_replaces_spaces_and_hyphens_with_underscores():
    assert StringSanitizer.sanitize_dir_name("My Song - Final Mix") == "my_song___final_mix"


# --- sanitize_dir_permit_increment: CuemsDBProject.new's unix_name candidate -


def test_sanitize_dir_permit_increment_keeps_hyphens_unlike_the_other_two():
    """The one method that does **not** replace ``-`` with ``_`` — its whole
    reason to exist separately from ``sanitize_dir_name`` is to permit the
    ``-NNN`` versioning suffix ``CopyMoveVersioned`` appends on collision."""
    assert StringSanitizer.sanitize_dir_permit_increment("My Project - v2!!") == "my_project_-_v2"


def test_sanitize_dir_permit_increment_replaces_spaces_but_not_hyphens():
    assert StringSanitizer.sanitize_dir_permit_increment("a b-c") == "a_b-c"


def test_sanitize_dir_permit_increment_strips_dots():
    assert StringSanitizer.sanitize_dir_permit_increment("v1.2.3") == "v123"
