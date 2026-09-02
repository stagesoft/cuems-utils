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

    # -- ITEM C: ported from cuems-nodeconf's CuemsNodeConf (feature 008) ----
    #
    # Characterized against ``CuemsNodeConf.py`` (research R7, E23) before
    # porting — ``tests/contract/test_nodeindex_characterization.py``. Every
    # method below is the daemon's algorithm unchanged; what moved is that
    # discovery is **passed in**, never reached for via ``self.listener``,
    # which is what makes these pinnable by a test that owns no avahi socket.

    def merge(self, discovered) -> None:
        """Match ``discovered`` into ``self`` by ``uuid`` (research R7).

        ``discovered`` is itself MAC-keyed (or however its own listener keys
        it) — ``self`` is matched against it by **uuid**, the node-identity
        model's stable primary key. Keying the merge on the MAC derived from
        an Avahi service name is what produced a duplicate controller entry
        in the daemon: the controller advertises its service as
        ``'controller'``, not its MAC, so a MAC-keyed merge orphaned the real
        entry's ``adopted``/``role_id``/``alias``/``hostname``.

        Args:
            discovered: a mapping of freshly-discovered nodes, keyed however
                the caller's discovery mechanism keys them.
        """
        existing_by_uuid = {
            n.get("uuid"): (key, n) for key, n in self.items() if n.get("uuid")
        }

        discovered_uuids = set()
        for discovered_node in discovered.values():
            d_uuid = discovered_node.get("uuid")
            if d_uuid:
                discovered_uuids.add(d_uuid)

            match = existing_by_uuid.get(d_uuid)
            if match is not None:
                _key, existing_node = match
                preserved_adopted = existing_node.get("adopted", False)
                # Refresh mutable discovery fields in place; never clobber
                # the real key with the discovered one.
                existing_node.update(
                    {k: v for k, v in discovered_node.items() if k != "mac"}
                )
                existing_node["adopted"] = preserved_adopted
                existing_node["online"] = True
            else:
                key = discovered_node.get("mac")
                self[key] = discovered_node
                self[key]["adopted"] = False
                self[key]["online"] = True

        for existing_node in self.values():
            if existing_node.get("uuid") not in discovered_uuids:
                existing_node["online"] = False

    def adopt(self, node_uuid) -> bool:
        """Adopt the node named by ``node_uuid``.

        Returns:
            bool: ``True`` if adopted (including "was already adopted"),
            ``False`` if the node is not present or is offline.
        """
        for n in self.values():
            if n.get("uuid") == node_uuid:
                if n.get("adopted"):
                    return True
                if not n.get("online"):
                    return False
                n["adopted"] = True
                return True
        return False

    def unadopt(self, node_uuid) -> bool:
        """Unadopt the node named by ``node_uuid`` — refuses the controller.

        Returns:
            bool: ``True`` if unadopted (including "was already unadopted"),
            ``False`` if the node is not present or is the controller.
        """
        for n in self.values():
            if n.get("uuid") == node_uuid:
                if n.get("node_role") is NodeRole.controller:
                    return False
                n["adopted"] = False
                return True
        return False

    def set_controller_always_adopted(self) -> None:
        """The controller is always adopted; on a first run, nothing else is."""
        for n in self.values():
            if n.get("node_role") is NodeRole.controller:
                n["adopted"] = True

    def missing_adopted(self, discovered) -> tuple:
        """Adopted nodes not present among ``discovered`` — for reporting.

        Returns:
            tuple: the adopted node objects that are not currently discovered.
        """
        discovered_uuids = {n.get("uuid") for n in discovered.values()}
        return tuple(
            n for n in self.values()
            if n.get("adopted") and n.get("uuid") not in discovered_uuids
        )

    def signature(self) -> tuple:
        """A stable signature of the persisted fields, order-independent.

        Sorted by key so two indexes holding the same nodes under the same
        keys agree regardless of insertion order — what
        ``CuemsNetworkMapType.refresh`` compares to decide whether a write is
        needed at all.
        """
        sig = []
        for key in sorted(self.keys()):
            n = self[key]
            role = n.get("node_role")
            role = role.value if isinstance(role, NodeRole) else role
            sig.append((
                key, n.get("uuid"), role, n.get("ip"),
                bool(n.get("adopted", False)), bool(n.get("online", False)),
                n.get("role_id"), n.get("alias"), n.get("hostname"),
            ))
        return tuple(sig)
