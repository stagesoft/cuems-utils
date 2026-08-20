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

## Two things that do not change

``node_type`` carries the string ``"NodeType.master"`` / ``"NodeType.slave"``.
That spelling is a **cross-repo wire contract** with ``cuems-engine``, which
compares against it directly, and it is not a Python enum here — the schema
types the element as ``NonEmptyString``. Turning it into an enum would be a
file-format change disguised as a cleanup.

``adopted`` and ``online`` stay **strings**. They are ``cms:BoolType`` in the
schema, which the show adapter table would decode to Python ``bool`` — and
``NetworkMap.get_nodes_by_adoption`` calls ``strtobool`` on them, the recorded
goldens carry ``"True"``, and ``cuems-engine`` branches on the string form. See
``config/base.py``'s ``from_decoded`` for why the adapters do not run here.
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
        "node_type": Unset,
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


class PutType(ConfigDict):
    """Declared in ``network_map.xsd`` and referenced by no element.

    Distinct from ``project_mappings.xsd``'s ``PutType`` — different field set
    (no ``id``), different schema, therefore a different class. Registries are
    per schema (research R4) and a class bound in two of them makes its
    coercion table ambiguous by construction.
    """

    DECLARED_DEFAULTS = {
        "name": Unset,
        "mappings": Unset,
    }


class CuemsNetworkMapType(ConfigDict):
    """The document root — what ``ConfigManager.network_map`` holds.

    Bound by element path: the root type is anonymous (research R3). Making the
    root an object is what takes ``network_map`` off FR-014's "raw nested dict"
    list; its ``node_list`` value stays a list of ``{"node": <node>}`` wrappers,
    because that is what ``cuems-engine`` iterates.
    """

    DECLARED_DEFAULTS = {"node_list": Unset}
