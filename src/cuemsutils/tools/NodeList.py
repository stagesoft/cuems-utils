"""The node model's public face (T018, data-model.md §3) — **public**.

Distinct from ``cuemsutils.config.network_map``, which stays **internal**
(FR-007, research R10a): the schema-bound containers (``node``, ``node_list``,
``CuemsNetworkMapType``) live there because the registry and the coherence
check need to reach them, and ``config/`` cannot import ``tools/`` without
closing an import cycle (``xml/registry.py`` imports ``config/network_map.py``;
``tools/ConfigManager.py`` imports ``xml/``). The classes ported in from
``cuems-nodeconf`` — the ones a consumer actually names — land here instead,
beside ``ConfigBase`` and ``ConfigManager``, which D15 already names as the
public configuration façade.
"""

from __future__ import annotations

from enum import Enum


class NodeRole(Enum):
    """The node role vocabulary — one definition, replacing three.

    Member **values** are exactly ``network_map.xsd``'s ``NodeRoleType``
    ``xs:enumeration`` facets (contract C1, asserted against the loaded schema
    rather than hand-copied). That identity is what lets ``_EnumAdapter``
    serialize without a mapping table: ``to_lexical`` returns
    ``str(obj.value)``, so the writer emits ``controller`` because the enum
    *value* says so.

    Replaces ``cuems-nodeconf``'s ``CuemsNode.node.NodeType``,
    ``AvahiTool.NodeType``, and the vocabulary that existed only as string
    literals in ``cuems-engine`` and three ``cuems-common`` tools.

    **Migration of meaning** (not of storage — nothing stores the old names
    after conversion): ``master`` -> ``controller``, ``slave`` -> ``node``,
    ``firstrun`` -> ``firstrun``.
    """

    controller = "controller"
    node = "node"
    firstrun = "firstrun"
