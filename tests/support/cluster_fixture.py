# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""A fixture cluster on disk — feature 012, T001.

One builder for the shape every phase of this feature measures against: a
configuration directory holding the three documents ``cuems-init-node`` writes,
plus a project library holding ``projects/<name>/{mappings.xml,<script>}`` and a
mirrored ``trash/projects/``.

**Documents are written as authored text, not through the library's writer.**
That is the point of the fixture rather than a shortcut: most of what this
feature must survive is a document the *tightened* schema refuses — a uuid1
identity, two rows sharing one — and the writer validates. A fixture that could
only produce valid documents could not build the input to a single one of US2's
tests.

The three knobs the tasks name are the three parameters: how many nodes, what
identity shape each carries, and what the script file is called. The script
filename is a parameter because the re-mint finds scripts by **root element**
(research R3), and a fixture that only ever wrote ``script.xml`` would let a
filename assumption pass unnoticed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: The not-provisioned placeholder. Admitted by the narrowed schemas, never
#: converged (data-model §1.2).
SENTINEL = "00000000-0000-0000-0000-000000000000"
SENTINEL_MAC = "000000000000"

#: One identity per shape the classification has to tell apart (data-model
#: §1.3). ``uuid1`` and ``uuid5`` are real values of their versions — the
#: version nibble is the third group's first character, so these are not
#: uuid4s with a digit changed but the shapes production actually carries.
SHAPES: dict[str, str] = {
    "uuid4": "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",
    "uuid4b": "b2a41f0c-7d3e-4a11-9c02-1f3e5d7a9b01",
    "uuid1": "0367f391-ebf4-11b2-9f26-000000000001",
    "uuid5": "74738ff5-5367-5958-9aee-98fffdcd1876",
    "uuid4upper": "6F1D2C3B-4A5E-4F60-8A71-9B8C7D6E5F41",
    "sentinel": SENTINEL,
    "nonsense": "not-a-uuid-at-all",
}

_NS = 'xmlns:cms="https://stagelab.coop/cuems/"'


def mac_for(index: int) -> str:
    """A distinct, plausible MAC per node. Keyed on the index so two nodes
    sharing an *identity* still differ by MAC — which is the collision case
    (data-model §4) and would be unrepresentable if the MAC were derived from
    the identity."""
    return f"aabbccdd{index:04x}"


@dataclass
class NodeSpec:
    """One node's row as the fixture will write it."""

    uuid: str
    mac: str
    role: str = "node"
    name: str = "node"
    ip: str = "10.0.0.1"
    adopted: str = "True"
    online: str = "True"


@dataclass
class Cluster:
    """Where the builder put everything, so a test can name any of it."""

    root: Path
    conf: Path
    library: Path
    nodes: list[NodeSpec]
    avahi: Path
    projects: list[str] = field(default_factory=list)
    script_name: str = "script.xml"

    @property
    def controller(self) -> NodeSpec:
        return next(n for n in self.nodes if n.role == "controller")

    def project_dir(self, name: str, trashed: bool = False) -> Path:
        base = self.library / ("trash/projects" if trashed else "projects")
        return base / name

    def script_path(self, name: str, trashed: bool = False) -> Path:
        return self.project_dir(name, trashed) / self.script_name

    def mappings_path(self, name: str, trashed: bool = False) -> Path:
        return self.project_dir(name, trashed) / "mappings.xml"

    def every_file(self) -> list[Path]:
        """Every document the fixture wrote, configuration and library alike."""
        return sorted(p for p in self.root.rglob("*.xml") if p.is_file())


# -- the three configuration documents -------------------------------------------------


def settings_xml(uuid: str, mac: str, library_path: str, version: int = 2) -> str:
    """``settings.xml``, complete enough for the strict read path to accept it
    when the identity shape allows (the seed values are ``make_defaults``')."""
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        f'<cms:CuemsSettings {_NS} doc_version="{version}"><Settings>'
        "<conf_path>/etc/cuems</conf_path>"
        f"<library_path>{library_path}</library_path>"
        "<tmp_path>/tmp/cuems</tmp_path>"
        "<database_name>project-manager.db</database_name>"
        "<show_lock_file>show.lock</show_lock_file>"
        "<editor_url>formitgo.local</editor_url>"
        "<controller_url>controller.local</controller_url>"
        "<templates_path>/usr/share/cuems</templates_path>"
        "<controller_interfaces_template>interfaces.controller</controller_interfaces_template>"
        "<node_interfaces_template>interfaces.node</node_interfaces_template>"
        "<controller_lock_file>controller.lock</controller_lock_file>"
        f"<node><uuid>{uuid}</uuid><mac>{mac}</mac>"
        "<osc_dest_host>localhost</osc_dest_host>"
        "<oscquery_ws_port>9190</oscquery_ws_port><oscquery_osc_port>9191</oscquery_osc_port>"
        "<websocket_port>9092</websocket_port><load_timeout>15000</load_timeout>"
        "<nodeconf_timeout>5000</nodeconf_timeout><discovery_timeout>15000</discovery_timeout>"
        "<mtc_port>Midi Through Port-0</mtc_port><osc_in_port_base>7000</osc_in_port_base>"
        "<nng_hub_port>9093</nng_hub_port><gradient_osc_port>7100</gradient_osc_port>"
        "<videoplayer><path>/usr/bin/cuems-videocomposer</path><args /><outputs>2</outputs>"
        "<osc_port>7000</osc_port><output_latency_ms>auto</output_latency_ms></videoplayer>"
        "<audioplayer><path>/usr/bin/cuems-audioplayer</path><args>-w -1</args>"
        "<output_latency_ms>auto</output_latency_ms></audioplayer>"
        "<audiomixer><path>/usr/bin/jack-volume</path><args /></audiomixer>"
        "<dmxplayer><path>/usr/bin/cuems-dmxplayer</path><args />"
        "<output_latency_ms>35</output_latency_ms></dmxplayer>"
        "</node></Settings></cms:CuemsSettings>\n"
    )


def network_map_xml(nodes: list[NodeSpec], version: int = 1) -> str:
    rows = "".join(
        f"<node><uuid>{n.uuid}</uuid><mac>{n.mac}</mac><name>{n.name}</name>"
        f"<node_role>{n.role}</node_role><ip>{n.ip}</ip>"
        f"<adopted>{n.adopted}</adopted><online>{n.online}</online></node>"
        for n in nodes
    )
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        f'<cms:CuemsNetworkMap {_NS} doc_version="{version}">'
        f"<node_list>{rows}</node_list></cms:CuemsNetworkMap>\n"
    )


def project_mappings_xml(nodes: list[NodeSpec], version: int = 1,
                         default_video: str = "") -> str:
    """``project_mappings``, used for both ``default_mappings.xml`` and a
    project's own ``mappings.xml`` — one schema, two filenames."""
    entries = "".join(
        f"<node><uuid>{n.uuid}</uuid><mac>{n.mac}</mac></node>" for n in nodes
    )
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        f'<cms:CuemsProjectMappings {_NS} doc_version="{version}">'
        f"<number_of_nodes>{len(nodes)}</number_of_nodes>"
        "<defaults>"
        "<default class=\"audio\" direction=\"input\"/>"
        "<default class=\"audio\" direction=\"output\"/>"
        "<default class=\"video\" direction=\"input\"/>"
        f"<default class=\"video\" direction=\"output\">{default_video}</default>"
        "<default class=\"dmx\" direction=\"input\"/>"
        "<default class=\"dmx\" direction=\"output\"/>"
        "</defaults>"
        f"<nodes>{entries}</nodes><new_nodes /></cms:CuemsProjectMappings>\n"
    )


def script_xml(name: str, nodes: list[NodeSpec], cue_id: str | None = None) -> str:
    """A show script whose video outputs carry the **compound**
    ``<identity>_<output>`` form (research R12, FR-009).

    The compound values are why literal substitution is the instrument: a
    structural rewrite would update the mappings above and leave every one of
    these stale *and schema-valid*, because ``output_name`` is a
    ``NameStringType`` and stays one (data-model §1.1a).
    """
    cue_id = cue_id or "12345678-aaaa-4aaa-abcd-123456789000"
    cues = "".join(
        "<VideoCue>"
        + _common(f"{i:08x}-bbbb-4bbb-abcd-1234567890{i:02d}", f"cue {i}")
        + "<Media><file_name>v.mp4</file_name><id />"
        "<duration><CTimecode>00:00:10.000</CTimecode></duration>"
        "<regions><Region><id>0</id><loop>0</loop>"
        "<in_time><CTimecode>00:00:00.000</CTimecode></in_time>"
        "<out_time><CTimecode>00:00:10.000</CTimecode></out_time></Region></regions></Media>"
        "<outputs>"
        + _video_output(f"{n.uuid}_0")
        + _video_output(f"{n.uuid}_custom_1")
        + "</outputs></VideoCue>"
        for i, n in enumerate(nodes)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<cms:CuemsProject {_NS} doc_version="2"><CuemsScript>'
        f"<CueList>{_common(cue_id, 'main')}<contents>{cues}</contents></CueList>"
        f"<description /><id>{cue_id}</id><name>{name}</name>"
        "<created>2026-09-30T00:00:00</created><modified>2026-09-30T00:00:00</modified>"
        "<ui_properties />"
        "</CuemsScript></cms:CuemsProject>\n"
    )


def _common(identifier: str, name: str) -> str:
    """``CommonPropertiesType``'s twelve required children, in schema order.

    Spelled out rather than abbreviated because the sequence is *ordered* and
    every element is required — an abbreviated cue is not a smaller fixture, it
    is an invalid document, and this fixture has to be able to produce valid
    ones too (T029a).
    """
    return (
        "<autoload>False</autoload><description />"
        f"<enabled>True</enabled><id>{identifier}</id><loop>0</loop><name>{name}</name>"
        "<offset><CTimecode>00:00:00.000</CTimecode></offset><post_go>pause</post_go>"
        "<postwait><CTimecode>00:00:00.000</CTimecode></postwait>"
        "<prewait><CTimecode>00:00:00.000</CTimecode></prewait>"
        "<target /><timecode>False</timecode><ui_properties />"
    )


def _video_output(output_name: str) -> str:
    return (
        f"<VideoCueOutput><output_name>{output_name}</output_name>"
        "<output_geometry><x_scale>1</x_scale><y_scale>1</y_scale>"
        "<corners><top_left><x>0</x><y>0</y></top_left>"
        "<top_right><x>1</x><y>0</y></top_right>"
        "<bottom_left><x>0</x><y>1</y></bottom_left>"
        "<bottom_right><x>1</x><y>1</y></bottom_right></corners>"
        "</output_geometry></VideoCueOutput>"
    )


def avahi_service_xml(uuid: str) -> str:
    """The live record ``cuems-nodeconf`` derives from ``settings.xml`` (D14,
    shape B). The check reads it as the fourth identity location."""
    services = "".join(
        f'<service protocol="ipv4"><type>_cuems_{kind}._tcp</type><port>9000</port>'
        f"<txt-record>node_role=node</txt-record><txt-record>uuid={uuid}</txt-record></service>"
        for kind in ("nodeconf", "osc")
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<service-group><name replace-wildcards="yes">%h</name>{services}</service-group>\n'
    )


# -- the builder -----------------------------------------------------------------------


def build_cluster(
    root: Path,
    *,
    shapes: list[str] | None = None,
    identities: list[str] | None = None,
    projects: int = 2,
    script_name: str = "script.xml",
    trashed_projects: int = 1,
    with_project_mappings: bool = True,
    self_index: int = 0,
    library_path: str | None = None,
    with_avahi: bool = True,
) -> Cluster:
    """Write a whole cluster under ``root`` and return where everything landed.

    Args:
        shapes: one :data:`SHAPES` key per node, in order. The first node is the
            controller. Defaults to two converged nodes.
        identities: explicit identities, overriding ``shapes`` — this is how a
            **collision** fixture is built, by naming one value twice.
        projects: how many live projects to write.
        script_name: what the script file is called in every project. Vary it to
            prove the reach does not depend on the name (research R3).
        trashed_projects: how many projects to mirror under ``trash/projects/``.
        with_project_mappings: whether each project carries its own
            ``mappings.xml``. It is optional per project (research R7/R10), so a
            fixture must be able to omit it.
        self_index: which node's identity ``settings.xml`` carries — i.e. which
            node of the cluster this directory *is*.
        with_avahi: whether to write the live Avahi record. It is the fourth
            identity location the check reads, and its *absence* is class 2 on
            a provisioned node — so a fixture that omitted it would report
            "absent" for every test that meant to measure something else.
    """
    if identities is None:
        keys = shapes or ["uuid4", "uuid4b"]
        identities = [SHAPES[k] for k in keys]
    nodes = [
        NodeSpec(
            uuid=uuid,
            mac=mac_for(i),
            role="controller" if i == 0 else "node",
            name=f"node{i}",
            ip=f"10.0.0.{i + 1}",
        )
        for i, uuid in enumerate(identities)
    ]

    root = Path(root)
    conf = root / "etc" / "cuems"
    library = root / "library"
    conf.mkdir(parents=True, exist_ok=True)
    for sub in ("projects", "media", "trash/projects", "trash/media"):
        (library / sub).mkdir(parents=True, exist_ok=True)

    me = nodes[self_index]
    (conf / "settings.xml").write_text(
        settings_xml(me.uuid, me.mac, library_path or str(library)), encoding="utf-8"
    )
    (conf / "network_map.xml").write_text(network_map_xml(nodes), encoding="utf-8")
    (conf / "default_mappings.xml").write_text(project_mappings_xml(nodes), encoding="utf-8")

    names = [f"project_{i}" for i in range(projects)]
    for trashed in (False, True):
        chosen = names[:trashed_projects] if trashed else names
        for name in chosen:
            directory = library / ("trash/projects" if trashed else "projects") / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / script_name).write_text(script_xml(name, nodes), encoding="utf-8")
            if with_project_mappings:
                (directory / "mappings.xml").write_text(
                    project_mappings_xml(nodes), encoding="utf-8"
                )

    avahi = root / "etc" / "avahi" / "services" / "cuems.service"
    if with_avahi:
        avahi.parent.mkdir(parents=True, exist_ok=True)
        avahi.write_text(avahi_service_xml(me.uuid), encoding="utf-8")

    return Cluster(root=root, conf=conf, library=library, nodes=nodes, avahi=avahi,
                   projects=names, script_name=script_name)


def snapshot(paths) -> dict[str, tuple[int, bytes, float]]:
    """``path -> (size, sha-able bytes, mtime_ns)`` for a no-write assertion.

    Carries the bytes **and** the modification time because this feature has a
    requirement in each direction: the check must change neither (FR-003), and a
    rewritten library file must change the *time* while keeping the size
    (FR-011b) — a length-preserving rewrite is invisible to the replication
    without it (research R11).
    """
    import os

    out = {}
    for path in paths:
        stat = os.stat(path)
        out[str(path)] = (stat.st_size, Path(path).read_bytes(), stat.st_mtime_ns)
    return out
