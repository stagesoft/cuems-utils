"""G3, T061/T062 — every schema's root instance saves through this
library's own write path unmodified (FR-023, SC-005), and a cue built
from a cue instance saves as part of a script, and each nested type
instance consumers name saves as part of its containing document
(FR-024).
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.mapper import Mapper
from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.spec import TypeKey

CONFIG_SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings")


@pytest.mark.parametrize("schema_name", CONFIG_SCHEMAS)
def test_a_config_root_instance_saves_through_config_save(schema_name, tmp_path):
    reg = get_registry(schema_name)
    td = SchemaDescriptor().describe(TypeKey(schema_name, reg.root, is_path=True))
    document = Mapper(schema_name).decode_config(td.instance)

    target = tmp_path / f"{schema_name}.xml"
    document.save(str(target))

    assert target.exists()


def test_the_script_root_instance_saves_through_project_save(tmp_path):
    td = SchemaDescriptor().describe(TypeKey("script", "CuemsProject", is_path=True))
    script = CuemsScript.from_json(td.instance["CuemsScript"])

    target = tmp_path / "script.xml"
    script.save(str(target))

    assert target.exists()


def test_a_cue_built_from_the_descriptor_instance_saves_through_project_save(tmp_path):
    """T062 — a single named cue type, built from its own descriptor
    instance, saves as part of a script. The script's own ``CueList``
    carries exactly this one cue."""
    cue_td = SchemaDescriptor().describe(TypeKey("script", "AudioCueType"))
    script_td = SchemaDescriptor().describe(TypeKey("script", "CuemsProject", is_path=True))

    script_body = script_td.instance["CuemsScript"]
    script_body["CueList"]["contents"] = [{"Cue": cue_td.instance}]

    script = CuemsScript.from_json(script_body)
    target = tmp_path / "with_cue.xml"
    script.save(str(target))

    assert target.exists()


@pytest.mark.parametrize(
    "schema_name,type_name",
    [
        ("script", "AudioCueOutputsType"),
        ("script", "VideoCueOutputsType"),
        ("script", "DmxCueOutputsType"),
    ],
)
def test_a_named_cue_output_instance_saves_as_part_of_its_cue(schema_name, type_name, tmp_path):
    """FR-024 — each nested type instance consumers name (the cue-output
    types quickstart's own example queries) saves as part of its
    containing document, not merely in isolation."""
    class_by_type = {"AudioCueOutputsType": "audio", "VideoCueOutputsType": "video", "DmxCueOutputsType": "dmx"}
    cue_type_by_class = {"audio": "AudioCueType", "video": "VideoCueType", "dmx": "DmxCueType"}
    device_class = class_by_type[type_name]

    output_td = SchemaDescriptor().describe(TypeKey(schema_name, type_name))
    cue_type = cue_type_by_class[device_class]
    cue_td = SchemaDescriptor().describe(TypeKey(schema_name, cue_type))

    output_body = output_td.instance
    if type_name == "VideoCueOutputsType":
        # VideoCueOutput's own constructor classifies output_name against
        # an "<uuid>_<int>" shape to pick alias/custom handling — a
        # Python-model rule with no XSD facet behind it, so no seeding
        # rule derives it. The generic NameStringType seed is what a
        # consumer replaces with a real target, exactly as a real file
        # name or target uuid would be (data-model.md §3's own framing).
        # "custom", not "alias": the custom shape requires canvas_region,
        # which the seed already supplies as a populated optional field
        # (research R3 decision 3) — "alias" forbids it, which a bare
        # seeded output_name cannot satisfy either way.
        output_body["CueOutput"]["output_name"] = "00000000-0000-4000-8000-000000000000_custom_0"

    cue_body = cue_td.instance
    cue_body["outputs"] = [output_td.instance]

    script_td = SchemaDescriptor().describe(TypeKey("script", "CuemsProject", is_path=True))
    script_body = script_td.instance["CuemsScript"]
    script_body["CueList"]["contents"] = [{"Cue": cue_body}]

    script = CuemsScript.from_json(script_body)
    target = tmp_path / f"{type_name}.xml"
    script.save(str(target))

    assert target.exists()
