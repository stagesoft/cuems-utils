# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The build-time generator for the three default documents (feature 011, D2).

``python -m cuemsutils.xml.make_defaults --out DIR`` writes ``settings.xml``,
``network_map.xml`` and ``default_mappings.xml`` from the schema descriptor
and the seed values (``seed_values.py``), carrying the **reserved sentinel
identity** (D3) — never a minted uuid, so the package build is reproducible
and no two machines imaged from one package share a "real" identity.
``debian/rules`` invokes it through the just-built venv's interpreter.

Three guarantees, each tested in ``tests/contract/test_make_defaults.py``:

* **deterministic** — the module generates twice and refuses to install if
  the two differ, so a stray timestamp or a random id fails the build;
* **valid with nothing to repair** — every document validates (T1) and
  loads back through the library's strict path with no repair;
* **complete in both directions** — a required field with no seed value, or
  a seed entry naming no field, fails naming itself (FR-010).

``default_mappings.xml`` is generated here knowingly (spec FR-012): a node
must boot long before feature 014 retires that document. Every piece of it —
the ``project_mappings`` tables in the seed file, ``_default_mappings`` below,
and ``cuems-init-node``'s write path for it — **retires with feature 014**.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

from .seed_values import SENTINEL_IDENTITY, Tables, shipped, validate

DOCUMENT_NAMES = ("settings.xml", "network_map.xml", "default_mappings.xml")


def _settings(tables: Tables):
    # The descriptor-driven generator already builds this document (feature
    # 008, ITEM D); it reads the same seed values through ``seed_values``.
    from .descriptor import generate_settings_example

    return generate_settings_example()


def _network_map(tables: Tables, identity: dict):
    """One row — this node's — at the given identity, ``firstrun`` (practice 4)."""
    from ..config.network_map import CuemsNetworkMapType, node
    from ..tools.NodeList import NodeRole

    seed = tables["network_map"]["NodeType"]
    row = node({
        "uuid": identity["uuid"],
        "mac": identity["mac"],
        "name": seed["name"],
        "node_role": NodeRole(seed["node_role"]),
        "ip": seed["ip"],
    })
    return CuemsNetworkMapType({"node_list": [{"node": row}]})


def _default_mappings(tables: Tables, identity: dict):
    """Retires with feature 014 (FR-012). One node entry, no hardware, empty defaults."""
    from ..config import mappings as m

    root_values = dict(tables["project_mappings"]["CuemsProjectMappingsType"])
    entry = m.NodeMappingType({"uuid": identity["uuid"], "mac": identity["mac"]})
    entry.update(tables["project_mappings"].get("NodeMappingType", {}))
    return m.CuemsProjectMappingsType({
        **root_values,
        "nodes": [{"node": entry}],
        "new_nodes": None,
    })


def _build_documents(tables: Tables, identity: dict | None = None) -> dict:
    """The three model objects, keyed by file name (the tests patch this)."""
    identity = dict(identity or SENTINEL_IDENTITY)
    return {
        "settings.xml": _settings(tables),
        "network_map.xml": _network_map(tables, identity),
        "default_mappings.xml": _default_mappings(tables, identity),
    }


def build(tables: Tables | None = None, identity: dict | None = None) -> dict:
    """Validated model objects for the three documents (used by ``cuems-init-node``
    too, with a real identity). ``tables`` default to the shipped seed values."""
    tables = tables if tables is not None else shipped()
    validate(tables)
    return _build_documents(tables, identity)


def generate(out: Path, tables: Tables | None = None, identity: dict | None = None) -> dict[str, str]:
    """Write the three documents into ``out``; return ``{name: sha256}``."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    documents = build(tables, identity)
    digests = {}
    for name, document in documents.items():
        target = out / name
        document.save(target)  # T1 validation, atomic write
        _assert_loads_clean(name, target)
        digests[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    return digests


def _assert_loads_clean(name: str, target: Path) -> None:
    """The strict read path accepts the document with nothing to repair."""
    from .settings import NetworkMap, ProjectMappings, Settings
    from .validators import repair

    reader = {"settings.xml": Settings, "network_map.xml": NetworkMap, "default_mappings.xml": ProjectMappings}[name]
    document = reader(str(target)).get_dict()
    repairs = repair(document)
    if repairs:
        raise RuntimeError(f"{name}: generated document needed repair: {repairs}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cuemsutils.xml.make_defaults", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, type=Path, help="directory to write the three documents into")
    args = parser.parse_args(argv)

    # Determinism, asserted at build rather than assumed: two generations into
    # scratch directories must agree byte for byte before anything is installed.
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        a = generate(Path(first))
        b = generate(Path(second))
    if a != b:
        differing = sorted(name for name in a if a[name] != b.get(name))
        raise RuntimeError(f"generation is not deterministic: {differing} differ between two runs")

    digests = generate(args.out)
    for name, digest in digests.items():
        print(f"{args.out / name}: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
