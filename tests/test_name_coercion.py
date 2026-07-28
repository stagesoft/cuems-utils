"""Free-text fields must survive parsing verbatim.

Regression tests for ClickUp 869cqbpxa: ``CuemsParser.str_to_value`` used to
coerce every scalar regardless of its key, so a cue named ``n`` was saved as
``False``, one named ``1`` as int ``1``, and one named ``none`` collapsed to
``None`` -> ``<name/>`` -> a hard XSD ``minLength`` failure on save.
"""

import string
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cuemsutils.cues import AudioCue, CueList, CuemsScript
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml import XmlReaderWriter
from cuemsutils.xml.Parsers import STRING_TYPED_KEYS, CuemsParser

TMP_DIR = Path(__file__).parent / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# The strtobool truth abbreviations -- the single characters that used to break.
TRUTHY_TOKENS = ["y", "Y", "t", "T", "yes", "true", "on"]
FALSY_TOKENS = ["n", "N", "f", "F", "no", "false", "off"]
# Hit the ['none', 'null', ''] -> None branch, which raised on save.
NULLISH_TOKENS = ["none", "null"]

UUID_STR = "1f301cf8-dd03-4b40-ac17-ef0e5e7988be"


def _str_to_value(value, key=None):
    """Call the parser helper without needing a constructed parser."""
    return CuemsParser.str_to_value(None, value, key=key)


def _audio_cue(name="placeholder"):
    cue = AudioCue({
        "Media": Media({
            "file_name": "f.wav",
            "id": "",
            "duration": "00:00:00.000",
            "regions": [
                Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})
            ],
        }),
        "ui_properties": {"warning": None},
    })
    cue.name = name
    return cue


def _script(cue_name="placeholder"):
    cuelist = CueList({"contents": [_audio_cue(cue_name)]})
    cuelist.name = "main"
    script = CuemsScript({"CueList": cuelist})
    script.name = "proj"
    # Dates required by the CuemsScript schema assertion (modified >= created).
    now = datetime.now(timezone.utc).isoformat()
    script.created = now
    script.modified = now
    return script


def _roundtrip_cue_name(name, tmp_name):
    """Write a script whose cue is named ``name``, read it back, return the name."""
    path = str(TMP_DIR / tmp_name)
    writer = XmlReaderWriter(schema_name="script", xmlfile=path)
    writer.write_from_object(_script(name))
    assert writer.validate() is None
    loaded = XmlReaderWriter(schema_name="script", xmlfile=path).read_to_objects()
    return loaded.cuelist.contents[0].name


# ---------------------------------------------------------------------------
# str_to_value -- string-typed keys are never coerced
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("char", list(string.ascii_letters + string.digits))
@pytest.mark.parametrize("key", ["name", "description", "file_name"])
def test_single_characters_survive_for_string_typed_keys(char, key):
    """All 62 alphanumeric single characters must pass through untouched.

    18 of them (y/Y/t/T/n/N/f/F and the ten digits) used to be corrupted.
    """
    result = _str_to_value(char, key=key)
    assert result == char
    assert isinstance(result, str)


@pytest.mark.parametrize("token", TRUTHY_TOKENS + FALSY_TOKENS + NULLISH_TOKENS)
def test_boolean_and_nullish_words_survive_as_names(token):
    result = _str_to_value(token, key="name")
    assert result == token
    assert isinstance(result, str)


def test_every_string_typed_key_is_protected():
    """Guards the allowlist itself, including the defensive entries."""
    for key in STRING_TYPED_KEYS:
        assert _str_to_value("n", key=key) == "n"
        assert _str_to_value("1", key=key) == "1"
        assert _str_to_value("none", key=key) == "none"


# ---------------------------------------------------------------------------
# ...but coercion still happens everywhere it must
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["enabled", "autoload", "timecode", "loop"])
@pytest.mark.parametrize(
    "value,expected",
    [("true", True), ("false", False), ("True", True), ("False", False)],
)
def test_boolean_keys_still_coerce(key, value, expected):
    assert _str_to_value(value, key=key) is expected


def test_numeric_and_nullish_keys_still_coerce():
    assert _str_to_value("1", key="loop") == 1
    assert _str_to_value("42", key="master_vol") == 42
    assert _str_to_value("none", key="target") is None
    assert _str_to_value("", key="target") is None


def test_id_is_not_allowlisted_and_still_becomes_a_uuid():
    """'id' must stay coercible -- the Uuid() branch is the only thing that
    produces Uuid objects on parse."""
    assert "id" not in STRING_TYPED_KEYS
    assert isinstance(_str_to_value(UUID_STR, key="id"), Uuid)


def test_unkeyed_calls_are_unchanged():
    """The key argument is optional; existing callers pass one positional arg."""
    assert _str_to_value("n") is False
    assert _str_to_value("1") == 1
    assert _str_to_value("none") is None


# ---------------------------------------------------------------------------
# Full XML roundtrip through the editor's save path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["a", "n", "y", "t", "f", "N", "1", "0", "no", "on"])
def test_cue_name_survives_xml_roundtrip(name):
    assert _roundtrip_cue_name(name, f"test_name_coercion_{name}.xml") == name


@pytest.mark.parametrize("name", NULLISH_TOKENS)
def test_nullish_cue_name_no_longer_fails_validation(name):
    """These used to raise XMLSchemaValidationError (minLength=1) on save."""
    assert _roundtrip_cue_name(name, f"test_name_coercion_null_{name}.xml") == name


def test_parser_preserves_name_through_the_editor_save_path():
    """CuemsParser is what CuemsDBProject.update() runs on the frontend payload."""
    parsed = CuemsParser({"AudioCue": {"name": "n", "description": "off"}}).parse()
    assert parsed["name"] == "n"
    assert parsed["description"] == "off"


# ---------------------------------------------------------------------------
# output_name: currently shielded by outputsParser, but assert the consumer
# that would break first if that bypass is ever removed (plan section 4b/5).
# ---------------------------------------------------------------------------

def test_get_all_output_names_handles_numeric_output_name():
    """MediaCue.get_all_output_names slices output_name -- an int would raise
    TypeError: 'int' object is not subscriptable."""
    parsed = CuemsParser({
        "AudioCue": {
            "name": "cue",
            "outputs": {
                "AudioCueOutput": [
                    {"output_name": "1", "output_vol": "80", "channels": {}}
                ]
            },
        }
    }).parse()
    # Returns (node_id, output_id) tuples split at the UUID boundary.
    names = parsed.get_all_output_names()
    assert names == [("1", "")]
    assert all(isinstance(part, str) for pair in names for part in pair)
