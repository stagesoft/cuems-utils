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

# ``partition_by_adoption`` is resolved by the module ``__getattr__`` at the
# foot of this file, which ruff cannot see — hence the narrow suppression rather
# than a module-level binding, which would reintroduce the import cycle that
# ``__getattr__`` exists to avoid.
__all__ = ["NodeRole", "NodeIndex", "node", "partition_by_adoption"]  # noqa: F822


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

    def ensure(self, entry) -> bool:
        """Insert ``entry`` **by reference** if no node carries its ``uuid``.

        The one primitive for "this node's row exists" (feature 011, research
        R7 item 7; ``cuems-nodeconf``'s plan ``09-self-node-seeding.md`` §5
        option 1). ``cuems-init-node`` seeds the self-entry through it at
        provisioning; ``cuems-nodeconf``'s feature 003 seeds from
        ``settings.xml`` through the same call, so the map logic lives here
        (D22) and not in the daemon.

        Two rules, both contractual:

        * **Never ``merge`` for seeding** (practice 3): ``merge`` marks every
          node absent from its argument offline, so seeding through it asserts
          "nobody else is here" before discovery has run. This method touches no
          other row.
        * **The caller's object is inserted, not a copy** — the aliasing
          contract ``adopt``/``merge``/``refresh`` already honour (T091/T092):
          a later ``adopt`` on the index must be visible through the caller's
          reference. ``tests/contract/test_node_aliasing.py`` fails against a
          ``dict(entry)`` here.

        Keyed by ``entry["mac"]`` (practice 5: match by uuid, key by MAC).

        Returns:
            bool: ``True`` if inserted, ``False`` if a node with that uuid was
            already present (left untouched).
        """
        wanted = entry["uuid"]
        if any(n.get("uuid") == wanted for n in self.values()):
            return False
        self[entry["mac"]] = entry
        return True

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

        **Existing nodes are refreshed in place, and that is a contract**
        (T091/T092). The body's own comment says so for a narrower reason —
        never clobber the real key with the discovered one — but the
        consequence that binds callers is the aliasing: a caller's index and
        its document share these dictionaries, so this method must update the
        node it found rather than substitute the discovered one. Working on
        copies here is a breaking change; ``adopt``'s docstring has the full
        reasoning, and ``tests/contract/test_node_aliasing.py`` fails if it
        happens.

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
        """Adopt the node named by ``node_uuid``, **mutating it in place**.

        The in-place write is a **contract, not an implementation detail**
        (T091/T092). Callers hold the same node objects through more than one
        reference at once — ``cuems-nodeconf`` keys this index over the very
        dictionaries its ``network_map`` document holds in ``node_list``, so a
        flag set here is *already* visible in the document about to be
        serialised. That aliasing is what makes a concurrent adopt unlosable in
        a daemon that takes no lock across its worker loop and its comms
        thread: there is no private copy for the write to be lost into.

        **Rebinding a copy here is therefore a breaking change**, not a
        tidy-up, and it would break a consumer while leaving every suite green.
        ``tests/contract/test_node_aliasing.py`` fails if this stops writing
        through; see
        ``specs/010-consumer-migration/nodeconf-map-write-divergence.md`` §4.

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

        Mutates the node **in place**, and for the same contractual reason as
        :meth:`adopt`: see that method's docstring. Rebinding a copy here is a
        breaking change for callers that alias these node objects.

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
        """Mark every controller adopted. Nothing else is touched.

        There is deliberately **no first-run behaviour** here, and no parameter
        that could carry one. The daemon this was ported from also cleared every
        non-controller's ``adopted`` flag on a first run; ``cuems-nodeconf``
        deleted that branch in its feature 001 rather than asking for the
        parameter back, having measured it to have no reachable correct effect
        and one reachable harmful one — the flag was computed once and never
        reset, so on a resident daemon an operator's adoption was silently
        cleared by the next refresh tick, after the UI had been told it
        succeeded.
        """
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


# --- the published adoption split (feature 013, T057, FR-035) -----------------
#
# ``NetworkMap.partition_by_adoption`` is the non-mutating replacement for
# ``get_nodes_by_adoption``, and before this it lived only at
# ``cuemsutils.xml.settings`` — which a consumer may not import (clarification
# Q14). So the one correct way to split a network map was unreachable and the
# mutating method was the only option. This publishes it; the body does not move.
#
# **Why a module ``__getattr__`` and not an import.** The ``node`` import at the
# top of this file is ``from ..config.network_map import node`` and does not load
# ``xml.settings``. A module-level ``from ..xml.settings import NetworkMap``
# would load ``mapper``, which loads ``adapters``, and ``adapters`` calls
# ``_register_enums()`` at import time — which does ``from ..tools.NodeList
# import NodeRole`` while *this* module is still initializing. Placed beside the
# ``node`` import, before the ``NodeRole`` class statement, that raises
# ``ImportError`` on a partially initialized module.
#
# Resolving on first *access* instead means ``import cuemsutils.tools.NodeList``
# costs nothing and the cycle never forms, because by the time anyone touches
# the name both ``NodeRole`` and ``NodeIndex`` are defined.
#
# It returns the function **itself**, not a wrapper: a wrapper would be a second
# thing to keep in step with the signature, and
# ``test_partition_public.py`` asserts the identity.

_LAZY = {"partition_by_adoption": ("..xml.settings", "NetworkMap")}


def __getattr__(name: str):
    """Resolve ``partition_by_adoption`` on first access (FR-035)."""
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, holder = target
    from importlib import import_module

    module = import_module(module_name, __package__)
    return getattr(getattr(module, holder), name)


def __dir__() -> list[str]:
    """``dir()`` answers with the published names, lazy ones included.

    Without this, a lazily published name is invisible to ``dir()`` and to
    anything that enumerates the module — including the public-API snapshot,
    which is how this name is pinned (T061).
    """
    return sorted({*globals(), *_LAZY})
