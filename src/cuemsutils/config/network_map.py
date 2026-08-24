"""Models for ``network_map.xsd`` (T047) — **containers only**.

## The 006/007 boundary, stated because this is the one place 006 could overreach

D11 moves the node model in from ``cuems-nodeconf``, and that is **feature
007's** work. FR-014 requires ``network_map`` to return typed objects *here*.
Both hold only if the split is explicit:

- **006 (this file)** defines ``node`` and ``node_list`` as declared-field
  containers over the three types in ``network_map.xsd``, and binds them so the
  accessors stop handing back raw nested dicts.
- **007** fills in the migrated behaviour — the Avahi-adjacent helpers, the
  identity fields the current nodeconf model omits, the 106-case coercion
  regression test — and deletes ``cuems-nodeconf``'s copies.

006 must not implement the node behaviour: its evidence is a regression test
that lives in the other repository, and 007 owns bringing it across. Building
the containers here and the behaviour there is what lets both features be
independently green.

## What feature 007 changes here, now that both are true

006's "two things that do not change" no longer describes this file — 007's
whole premise is that both of them do, deliberately, for ``network_map`` only:

``node_type`` is renamed to ``node_role`` and is no longer free text.
``network_map.xsd`` retypes the element ``cms:NodeRoleType`` (an
``xs:string`` restricted to ``controller``/``node``/``firstrun``, replacing
``master``/``slave``/``firstrun``), and the registry's per-schema
``runs_adapter_table`` opt-in (research R1) makes ``Mapper.decode_config``
bind it to a real ``NodeRole`` enum rather than to the string
``"NodeType.master"`` ``cuems-engine`` used to compare against directly.
``mac``/``name``/``ip``/``role_id``/``alias``/``hostname`` are still free
text — no codec is bound to their XSD types, which is the structural form of
the coercion guarantee (research R4), not a name-matched exemption. ``uuid``
is typed too (``cms:UuidType``, canonical-hex shape) but keeps decoding to
raw text when a value doesn't parse as one — see ``adapters.py``'s
``_UuidAdapter``.

``adopted`` and ``online`` **do** decode to Python ``bool`` here now — the
same opt-in applies to every scalar field on this schema, not to ``node_role``
alone. ``NetworkMap.get_nodes_by_adoption`` accepts either the typed or the
pre-typing string shape (research R7, ``_as_bool``); ``settings``,
``project_mappings`` and ``project_settings`` did not opt in and keep
decoding ``cms:BoolType`` as the strings their recorded goldens carry. See
``config/base.py``'s ``from_decoded`` and ``mapper.py``'s ``decode_config``
for where that per-schema line is actually drawn.
"""

from __future__ import annotations

from ..helpers import Unset
from .base import ConfigDict


class node(ConfigDict):  # noqa: N801 - the domain's name, not a class-name style
    """One node's identity in the network map.

    Lowercase on purpose: ``node`` is what the element is called, what
    ``NetworkMap.get_node`` returns, and what every consumer already calls the
    thing. Naming it ``NodeIdentityType`` would be this file inventing a
    vocabulary the rest of the system does not use — and naming is exactly the
    part the derivation rule (data-model §1) leaves to a human.

    Three fields are optional and were added by ``feat/node-identity``:
    ``role_id`` (assigned by nodeconf during adoption), ``alias``
    (operator-defined) and ``hostname`` (transitional — only set for legacy
    nodes whose OS hostname differs from ``role_id``). They are declared and
    :data:`Unset`, so a document that omits them decodes to an object without
    the keys rather than to one carrying three empty strings. That is the
    schema evolution convention working as intended, on the schema that
    motivated writing it down.
    """

    DECLARED_DEFAULTS = {
        "uuid": Unset,
        "mac": Unset,
        "name": Unset,
        "node_role": Unset,
        "ip": Unset,
        "adopted": Unset,
        "online": Unset,
        "role_id": Unset,
        "alias": Unset,
        "hostname": Unset,
    }


class node_list(ConfigDict):  # noqa: N801 - the element's name
    """``NodeDictType`` — the repeated ``<node>`` container.

    **The decoded value at this position is a Python list, not an instance of
    this class**, and that is worth stating rather than discovering. The
    converter turns a repeated child into ``[{"node": {...}}, ...]`` as soon as
    the child's cardinality is not single, which ``NodeDictType``'s never is —
    so a document always yields a list and this class is never instantiated by
    decode.

    It exists anyway for two reasons that are not "completeness": the registry
    requires a binding for every complex type (C7), and the coherence check
    (T041) compares a declared field set against the schema's. Leaving the type
    ``GENERIC`` would exempt it from both.
    """

    DECLARED_DEFAULTS = {"node": Unset}


class CuemsNetworkMapType(ConfigDict):
    """The document root — what ``ConfigManager.network_map`` holds.

    Bound by element path: the root type is anonymous (research R3). Making the
    root an object is what takes ``network_map`` off FR-014's "raw nested dict"
    list; its ``node_list`` value stays a list of ``{"node": <node>}`` wrappers,
    because that is what ``cuems-engine`` iterates.
    """

    DECLARED_DEFAULTS = {"node_list": Unset}

    def save(self, path) -> None:
        """Validate, **then** write (research R6, contract C5).

        Mirrors ``CuemsScript.save`` — the write path's single entry point
        (``documents.build_tree``/``write_tree``) is schema-generic and needed
        no config-specific machinery, only a caller. Config has one validation
        tier: ``network_map.xsd`` declares no ``xs:assert`` (T2 semantic
        rules are a ``script.xsd`` concept), so this checks T1 only and raises
        on the first structural violation — a role value outside the
        enumeration is exactly that (FR-014).

        Does not mutate ``self``: ``build_tree`` reads declared fields through
        the adapters' ``to_lexical``/``to_wire``, never writing back into the
        object (FR-015) — the workaround ``cuems-nodeconf`` built (a separate
        serialization copy, because its old write path *did* mutate) has
        nothing left to work around.

        Args:
            path (str | os.PathLike): where to write.

        Raises:
            SchemaError: the document does not match ``network_map.xsd`` —
                carries the violation (FR-034b).
            OSError: propagated unwrapped, exactly as ``CuemsScript.save``.
        """
        from ..errors import SchemaError
        from ..xml.documents import build_tree, iter_schema_errors, write_tree
        from ..xml.validators import violation_from_schema_error

        tree = build_tree(self, "network_map")
        for error in iter_schema_errors("network_map", tree):
            violation = violation_from_schema_error(error)
            raise SchemaError(str(violation), violation=violation)
        write_tree(tree, path)
