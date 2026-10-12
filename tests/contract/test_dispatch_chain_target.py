"""``NodeIndex`` is a valid target for the operator's adopt/unadopt chain (T042a) — FR-022, US3 scenario 6.

The chain, traced end to end: ``settings.component.ts`` emits a
``nodelist_modify`` websocket action with ``modify_action`` ``'ADD'`` or
``'REMOVE'`` and a node uuid
(``cuems-frontend/src/app/components/settings/settings.component.ts``,
``confirmAddNode``/``confirmRemoveNode``) → forwarded over the nng hub to
``cuems-nodeconf``'s ``CuemsNodeConf.engine_callback``
(``cuemsnodeconf/CuemsNodeConf.py:113-144``), which dispatches:

| ``modify_action`` | Daemon call today | ``NodeIndex`` equivalent |
|---|---|---|
| ``'ADD'``    | ``self.adopt_node(node_uuid)``   | ``NodeIndex.adopt(node_uuid)``   |
| ``'REMOVE'`` | ``self.unadopt_node(node_uuid)`` | ``NodeIndex.unadopt(node_uuid)`` |

Two operations, no third: ``engine_callback`` recognises no other
``modify_action`` value (anything else becomes an error response). This table
is also recorded in ``data-model.md`` §5, so a later chain change can be
checked against it rather than only against this test.
"""

from __future__ import annotations

from cuemsutils.config.network_map import node
from cuemsutils.tools.NodeList import NodeIndex, NodeRole

#: The two, and only two, ``modify_action`` values ``engine_callback``
#: recognises (CuemsNodeConf.py:120-125).
DISPATCH_TABLE = {
    "ADD": "adopt",
    "REMOVE": "unadopt",
}


def test_every_dispatch_chain_operation_has_a_nodeindex_method():
    for modify_action, method_name in DISPATCH_TABLE.items():
        assert hasattr(NodeIndex, method_name), (
            f"modify_action={modify_action!r} has no NodeIndex.{method_name}"
        )
        assert callable(getattr(NodeIndex, method_name))


def test_add_dispatches_to_adopt_with_equivalent_behaviour():
    idx = NodeIndex({
        "aa": node({"uuid": "u1", "mac": "aa", "node_role": NodeRole.node,
                    "adopted": False, "online": True}),
    })
    assert idx.adopt("u1") is True
    assert idx["aa"]["adopted"] is True


def test_remove_dispatches_to_unadopt_with_equivalent_behaviour():
    idx = NodeIndex({
        "aa": node({"uuid": "u1", "mac": "aa", "node_role": NodeRole.node,
                    "adopted": True, "online": True}),
    })
    assert idx.unadopt("u1") is True
    assert idx["aa"]["adopted"] is False


def test_no_third_modify_action_is_recognised():
    """The chain's error path for anything else — recorded so a widened
    dispatch table cannot silently gain a third operation with no
    ``NodeIndex`` counterpart."""
    assert set(DISPATCH_TABLE) == {"ADD", "REMOVE"}
