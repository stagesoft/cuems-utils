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
from functools import cache
from typing import Callable, Hashable

# Re-exported (FR-002b, FR-007) — the public path to the container a document
# decodes. ``cuemsutils.config`` itself exports nothing (research R10a); a
# consumer imports ``node`` from here, never from ``cuemsutils.config.network_map``.
from ..config.network_map import node
from ..helpers import Unset
from ..log import Logger

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

        **Only values the schema accepts are copied** (D12 of
        ``specs/planning/tpm-ek-fingerprint.md``). Each announced field is
        checked against its ``NodeType`` simple type, using the text ``save``
        would write. An invalid value is dropped with a warning, and the stored
        value stays. A new node missing a valid required field is not added.
        Without this, one bad announcement made every later ``save`` of the
        whole map fail, because the bad value stayed in memory. A field that is
        not announced (absent, ``None`` or ``Unset``) is left alone, and
        ``adopted``/``online`` are never taken from discovery. The merge itself
        never fails.

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

            accepted, rejected = _announced_fields(discovered_node)
            match = existing_by_uuid.get(d_uuid)
            if match is not None:
                _key, existing_node = match
                for name, value in rejected:
                    Logger.warning(
                        f"Node {d_uuid} announced an invalid {name} ({value!r}); "
                        f"keeping {existing_node.get(name)!r}"
                    )
                preserved_adopted = existing_node.get("adopted", False)
                # Refresh mutable discovery fields in place; never clobber
                # the real key with the discovered one.
                existing_node.update(
                    {k: v for k, v in accepted.items() if k != "mac"}
                )
                existing_node["adopted"] = preserved_adopted
                existing_node["online"] = True
            else:
                missing = [
                    name for name, (_t, required, _s) in _node_fields().items()
                    if required and name not in accepted
                ]
                if missing:
                    Logger.warning(
                        f"Discovered node {d_uuid!r} not added to the network map: "
                        f"no valid {', '.join(missing)}"
                    )
                    continue
                for name, value in rejected:
                    Logger.warning(
                        f"Node {d_uuid} announced an invalid {name} ({value!r}); dropped"
                    )
                    del discovered_node[name]
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

    def set_alias(self, node_uuid, alias: str | None) -> bool:
        """Set this node's operator-facing label (G4, contract C4).

        **Scope is ``alias`` only** (FR-042) — no general "set operator
        fields" call is offered, because it would invite writes to fields
        discovery overwrites.

        **Validates before mutating** (FR-036) — the clause with an incident
        behind it: an in-place empty label would make the subsequent
        ``save()`` fail *after* the index had already changed, and a
        resident daemon's pending-write retry would then fail on that same
        row until restart (``cuems-nodeconf``'s own R9).

        **Mutates in place** (FR-039), on the node object the document holds
        — the same aliasing contract :meth:`adopt` documents: callers hold
        these node objects through more than one reference, which is what
        makes a concurrent adopt (or label) unlosable in a daemon that takes
        no lock across its worker loop and its comms thread. Rebinding a
        copy would break a consumer while leaving every suite green.

        Liveness is **not** a precondition (FR-043), unlike :meth:`adopt` —
        an offline node and the controller are both labellable.

        Args:
            node_uuid: the identity of the node to label.
            alias: the new label, or ``None`` to **clear** it (removes the
                key — the element is optional). Setting it to the value it
                already has reports success and does not move
                :meth:`signature`, so a write-if-changed caller does not
                write (FR-038, FR-041).

        Returns:
            bool: ``False`` for an unknown ``node_uuid`` (nothing mutated);
            ``True`` otherwise — set, cleared, or already that value
            (FR-037, FR-038).

        Raises:
            ValueError: ``alias`` is present but empty or whitespace-only —
                raised **before** any node is touched (FR-036).
        """
        if alias is not None and not alias.strip():
            raise ValueError(
                f"NodeIndex.set_alias: {node_uuid}'s alias must be a "
                f"non-empty string or None to clear it, not {alias!r}. "
                "Pass a label with at least one non-space character."
            )
        for n in self.values():
            if n.get("uuid") == node_uuid:
                if alias is None:
                    n.pop("alias", None)
                else:
                    n["alias"] = alias
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

    # -- foreign-controller scoping ---------------------------------------------
    #
    # Several clusters can share one LAN, and every controller announces itself,
    # so ``merge`` + ``set_controller_always_adopted`` alone adopt the *other*
    # clusters' controllers into this map (observed in the field 2026-10-01 and
    # 2026-10-06). The rule is ``cuems-nodeconf``'s shipped fix (``80ccc83``),
    # moved here because the map mutation is this library's (D22). Requested in
    # ``cuems-nodeconf``'s ``specs/upstream-reports/foreign-controller-scoping.md``.
    #
    # **The rule.** A node's *cluster controllers* are, on a controller, exactly
    # its own uuid; on any other node, every ``controller``-role uuid its map
    # already records. An empty set means *no scoping* — today's first-come
    # behaviour. A *foreign controller* is a ``controller``-role node whose uuid
    # is outside a non-empty cluster set; it is ignored on discovery and
    # **removed** from the map, never marked offline (an offline row means
    # "ours, currently absent").
    #
    # **Known limitation, stated not fixed**: a *fresh* node whose first pass
    # hears two clusters' controllers has an empty set, accepts both, and from
    # then on both are its own. Fixing that needs a join protocol, which belongs
    # to ``cuems-nodeconf``'s controller election, not to this index.

    def cluster_controllers(self, own_uuid=None, own_role=None) -> frozenset:
        """The uuids of the controller(s) this node belongs to.

        Compute it **before** the pass's ``merge`` — computed after, the merge's
        own additions would define the cluster. Read-only.

        Args:
            own_uuid: this node's identity.
            own_role: this node's :class:`NodeRole`.

        Returns:
            frozenset: ``{own_uuid}`` on a controller with a uuid; otherwise the
            uuid of every ``controller``-role node in ``self`` that has one.
            Empty means "no scoping".
        """
        if own_role is NodeRole.controller and own_uuid:
            return frozenset({own_uuid})
        return frozenset(n["uuid"] for n in self.controllers if n.get("uuid"))

    @staticmethod
    def is_foreign_controller(n, cluster) -> bool:
        """``n`` is a controller and ``cluster`` is non-empty and excludes it."""
        return (
            n.get("node_role") is NodeRole.controller
            and bool(cluster)
            and n.get("uuid") not in cluster
        )

    def foreign_controllers(self, cluster) -> tuple:
        """The foreign controllers in ``self`` — the node objects themselves.

        Read-only. Exists so a caller can **log** what a scoped
        ``CuemsNetworkMapType.refresh`` is about to remove; ``refresh`` itself
        returns only whether it wrote.
        """
        return tuple(
            n for n in self.values() if self.is_foreign_controller(n, cluster)
        )

    def drop_foreign_controllers(self, cluster) -> tuple:
        """Delete every foreign controller's **key** from ``self``.

        Removal, not a flag flip, and no copying: every node that stays is the
        object it was (the aliasing contract :meth:`adopt` documents). An empty
        ``cluster`` removes nothing.

        Returns:
            tuple: the removed node objects.
        """
        doomed = [k for k, n in self.items() if self.is_foreign_controller(n, cluster)]
        return tuple(self.pop(k) for k in doomed)

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


#: Never taken from discovery: ``merge`` preserves ``adopted`` and forces
#: ``online``, so an announced value for either is not checked.
_DISCOVERY_MANAGED = frozenset({"adopted", "online"})


@cache
def _node_fields() -> dict:
    """``name -> (xsd_type, required, simple type)`` for ``NodeType``'s fields.

    Imported lazily: ``xml/`` imports this module while registering its enums,
    so a module-level import would close the cycle ``__getattr__`` avoids.
    """
    from ..xml.schema import simple_type
    from ..xml.spec import derive_named

    return {
        f.name: (f.xsd_type, f.required, simple_type("network_map", f.xsd_type))
        for f in derive_named("network_map", "NodeType").fields
    }


def _is_valid(name: str, value) -> bool:
    """Whether ``save`` would write ``value`` as text the schema accepts."""
    from ..xml.adapters import adapter_for

    xsd_type, _required, simple = _node_fields()[name]
    if simple is None:
        return True
    try:
        text = adapter_for(xsd_type).to_lexical(value)
    except (AttributeError, TypeError, ValueError):
        return False
    return simple.is_valid("" if text is None else text)


def _announced_fields(discovered_node) -> tuple[dict, list]:
    """Split a discovered node's announced fields into valid and invalid.

    Undeclared keys and keys with no value (``None``/``Unset``) are skipped,
    so they are in neither result: they are not announcements.
    """
    fields = _node_fields()
    accepted: dict = {}
    rejected: list = []
    for name, value in discovered_node.items():
        if name not in fields or name in _DISCOVERY_MANAGED or value is None or value is Unset:
            continue
        if _is_valid(name, value):
            accepted[name] = value
        else:
            rejected.append((name, value))
    return accepted, rejected


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
