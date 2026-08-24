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
from typing import Callable, Hashable

# Re-exported (FR-002b, FR-007) — the public path to the container a document
# decodes. ``cuemsutils.config`` itself exports nothing (research R10a); a
# consumer imports ``node`` from here, never from ``cuemsutils.config.network_map``.
from ..config.network_map import node  # noqa: F401

__all__ = ["NodeRole", "NodeIndex", "node"]


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


class NodeIndex(dict):
    """The MAC-keyed (or however the caller keys it) working set of nodes.

    ``cuems-nodeconf``'s ``node_list``/``CuemsNodeDict`` under a new name —
    ``node_list`` was taken by ``config/network_map.py``'s schema container
    (spec FR-002), a *different* shape despite the shared old name.

    **The key function is supplied by the caller, not hard-coded** (research
    R5). ``cuems-nodeconf`` keys this collection by MAC, and its own comment
    records that keying merges on the Avahi-derived MAC produced duplicate
    controller entries — the controller advertises as ``controller`` rather
    than as its MAC. The node-identity contract makes ``uuid`` the primary
    key. Moving this collection must not silently re-key it, so the choice
    stays with the caller: pass whichever function extracts the key from a
    :class:`~cuemsutils.config.network_map.node`.

    ``masters``, ``slaves`` and ``firstruns`` do not migrate: they name a
    vocabulary that no longer exists. ``nodes`` as a role selection on a
    collection *of* nodes would be ambiguous by construction — ``by_role``
    cannot be misread the way ``index.nodes`` could.
    """

    def __init__(self, nodes: dict | None = None):
        super().__init__(nodes or {})

    @classmethod
    def from_nodes(cls, nodes, key: Callable[[node], Hashable]) -> "NodeIndex":
        """Build from an iterable of nodes, keyed by ``key(node)``."""
        return cls({key(n): n for n in nodes})

    def by_role(self, role: NodeRole) -> tuple[node, ...]:
        """Every node whose ``node_role`` is ``role``."""
        return tuple(n for n in self.values() if n.get("node_role") == role)

    @property
    def controllers(self) -> tuple[node, ...]:
        """The one selection with a caller in every repository."""
        return self.by_role(NodeRole.controller)
