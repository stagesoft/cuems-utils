"""T081 — an atomic save preserves the target's permissions (feature 010, T080).

Reported upstream by ``cuems-nodeconf``'s feature 001, measured rather than
inferred: ``/etc/cuems/network_map.xml`` went in at ``0644`` and came back
``0600``.

``write_tree`` writes through ``tempfile.mkstemp``, which creates its file
``0600`` by construction, and ``os.replace`` carries the **temporary's** mode
onto the target. So every save silently discarded the document's permissions,
however the file had been installed.

**Why that is a defect and not a detail.** ``network_map.xml`` is the cluster's
topology and is read by processes that are not the one that wrote it:
``cuems-nodeconf`` runs as **root**, while ``cuems-controller-engine`` and
``cuems-node-engine`` run as ``User=cuems``. ``cuems-common`` ships the file
``0644`` precisely so the non-root engine can read it, so the first map write on
any node took the topology away from the engine — the same failure shape as the
root-owned ``/tmp/nodeconf.ipc`` crash-loop in that repository's history.

``write_tree`` is the single choke point for **every** document this package
writes — all four configuration domains through ``config.base.save_document``,
``CuemsScript.save``, and ``xml.convert_documents`` — so it is tested here
rather than once per domain. The parametrised case below is what stops this
being a ``network_map``-shaped fix.

POSIX only: ``os.chmod``'s group/other bits do not survive on Windows, and the
package's deployment target is Debian.
"""

from __future__ import annotations

import os
import stat
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX file modes; the package ships on Debian"
)


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def _tree():
    """A trivially valid tree — this module is about modes, not content."""
    from xml.etree.ElementTree import Element, ElementTree

    return ElementTree(Element("root"))


def _write(target):
    from cuemsutils.xml.documents import write_tree

    write_tree(_tree(), target)


# --------------------------------------------------------------------------
# The reported defect
# --------------------------------------------------------------------------


@pytest.mark.parametrize("existing", [0o644, 0o664, 0o600, 0o640])
def test_an_existing_target_keeps_its_own_mode(tmp_path, existing):
    """The report's measurement, generalised past the mode that produced it.

    ``0644`` is the one ``cuems-common`` ships and the one that broke; the other
    three are here so a fix that hard-codes ``0644`` fails rather than passes.
    """
    target = tmp_path / "network_map.xml"
    target.write_text("<root/>")
    os.chmod(target, existing)

    _write(target)

    assert _mode(target) == existing, (
        f"save reset the target from {existing:#o} to {_mode(target):#o}; a mode "
        "the operator or the package chose is not the writer's to discard"
    )


def test_a_new_target_is_readable_by_other_users(tmp_path):
    """When no target exists there is no mode to preserve — so don't leave 0600.

    The engine runs as a different user than the daemon that writes the map. A
    freshly created document that only its author can read is the same outage as
    the one above, arrived at from the other direction.
    """
    target = tmp_path / "fresh.xml"
    assert not target.exists()

    _write(target)

    mode = _mode(target)
    assert mode & stat.S_IRGRP, f"{mode:#o} is not group-readable"
    assert mode & stat.S_IROTH, f"{mode:#o} is not other-readable"
    assert not (mode & 0o111), f"{mode:#o} is executable; a document is not"


def test_a_new_target_respects_the_process_umask(tmp_path):
    """Default for a new file, but not louder than the umask allows.

    A process that has deliberately narrowed its umask is making a decision this
    package does not get to override.
    """
    target = tmp_path / "umasked.xml"
    previous = os.umask(0o027)
    try:
        _write(target)
    finally:
        os.umask(previous)

    assert not (_mode(target) & stat.S_IROTH), (
        f"{_mode(target):#o} is other-readable despite a 0027 umask"
    )


# --------------------------------------------------------------------------
# Every domain, not just the one that reported it
# --------------------------------------------------------------------------


def _network_map():
    from cuemsutils.config.network_map import CuemsNetworkMapType

    return CuemsNetworkMapType(node_list=[]), "network_map"


def _script():
    from tests.support import invalid_scripts as broken

    return broken.valid_script(), "script"


@pytest.mark.parametrize("factory", [_network_map, _script], ids=["network_map", "script"])
def test_every_public_save_path_preserves_the_mode(tmp_path, factory):
    """``write_tree`` is the choke point; this proves the public saves reach it.

    A fix applied inside one domain's ``save`` would pass the tests above and
    fail here, which is the point of the parametrisation.
    """
    obj, name = factory()
    target = tmp_path / f"{name}.xml"
    target.write_text("<placeholder/>")
    os.chmod(target, 0o644)

    obj.save(target)

    assert _mode(target) == 0o644


# --------------------------------------------------------------------------
# The contracts this must not break while fixing the mode
# --------------------------------------------------------------------------


def test_the_write_is_still_atomic_and_leaves_no_temporary(tmp_path):
    """Preserving the mode must not cost the atomicity it sits inside.

    ``write_tree``'s own contract: a temp file in the destination directory,
    then ``os.replace``. If a ``chmod`` step reintroduced a non-atomic path — or
    left the temporary behind on the happy path — this catches it.
    """
    target = tmp_path / "doc.xml"
    _write(target)

    assert target.exists()
    strays = [p.name for p in tmp_path.iterdir() if p.name != "doc.xml"]
    assert strays == [], f"temporary files left beside the target: {strays}"


def test_a_failed_write_leaves_the_target_untouched(tmp_path):
    """The non-mutation half of the contract, including the mode.

    A failure partway through must leave both the bytes *and* the permissions
    exactly as they were — a save that fails but still relaxes a mode is a
    quieter version of the same bug.
    """
    from cuemsutils.xml.documents import write_tree

    target = tmp_path / "doc.xml"
    target.write_text("<original/>")
    os.chmod(target, 0o640)

    class Exploding:
        def write(self, *a, **kw):
            raise RuntimeError("serialization failed partway")

    with pytest.raises(RuntimeError):
        write_tree(Exploding(), target)

    assert target.read_text() == "<original/>"
    assert _mode(target) == 0o640
    strays = [p.name for p in tmp_path.iterdir() if p.name != "doc.xml"]
    assert strays == [], f"temporary left behind after a failed write: {strays}"
