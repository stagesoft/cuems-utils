# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``cuems-init-node`` — node coherence, atomically (feature 011, D11–D13).

Writes the three documents ``ConfigManager`` needs — ``settings.xml``,
``network_map.xml`` and ``default_mappings.xml`` — as one set, with **one**
identity: preserved if ``settings.xml`` already carries a real uuid, minted
through :class:`cuemsutils.tools.Uuid` (the only minter in the ecosystem) if
it is absent or the sentinel, or taken from ``--uuid``. Site values come from
the shipped seed file plus the ``defaults.d`` overlay (``--no-overlay`` for
``postinst``, which must never read operator input). Operator edits to
non-identity fields are **kept** across re-runs, three-way against the write
record, and ``--reset`` returns to defaults. ``--check`` reads the four
identity locations and writes nothing.

Contract: ``specs/011-etc-cuems-first-install/contracts/cuems-init-node.md``.
Research: R5 (write record), R6 (atomic set), R8 (postinst mode), R14
(check), R15 (logging), R21 (identity-adjacent derivation, FR-025a).
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..xml.seed_values import SeedValueError
from .identity_check import (  # noqa: F401 — re-exported: the wording constants are this tool's public face
    FIX_NODECONF,
    FIX_PLAIN,
    FIX_RESET,
    FIX_UNMASK,
    NOT_PROVISIONED,
    SENTINEL,
)

__all__ = ["main", "NOT_PROVISIONED", "MODIFIED_KEPT", "FIX_PLAIN", "FIX_RESET", "FIX_NODECONF", "FIX_UNMASK"]

MODIFIED_KEPT = "modified, kept"
DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")
SCHEMA_OF = {"settings.xml": "settings", "network_map.xml": "network_map", "default_mappings.xml": "project_mappings"}
SENTINEL_MAC = "000000000000"
DEFAULT_CONF_DIR = "/etc/cuems"
DEFAULT_STATE_DIR = "/var/lib/cuems-utils"
DEFAULT_OVERLAY_DIR = "/etc/cuems/defaults.d"
DEFAULT_LOCK = "/run/lock/cuems-init-node.lock"
DEFAULT_SYSFS = "/sys/class/net"
IDENTITY_PATHS = frozenset({"node.uuid", "node.mac", "self.uuid", "self.mac", "node_entry.uuid", "node_entry.mac"})
VIRTUAL_PREFIXES = ("veth", "docker", "br-", "virbr", "tap", "tun", "wg", "vnet", "dummy")


class Refusal(Exception):
    """Refused before writing anything (exit 1)."""


class Unreadable(Exception):
    """A required input cannot be read (exit 2)."""


# -- arguments -------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cuems-init-node", description=__doc__.split("\n\n")[1])
    p.add_argument("--uuid", help="the identity to assign (uuid4); otherwise preserved or minted")
    p.add_argument("--mac", help="the node's MAC (12 hex); otherwise from ethernet0 or the first physical interface")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--overlay", default=DEFAULT_OVERLAY_DIR, help=f"site overlay directory (default {DEFAULT_OVERLAY_DIR})")
    group.add_argument("--no-overlay", action="store_true", help="read no operator input (what postinst passes)")
    p.add_argument("--install-missing", action="store_true", help="create only absent documents; never rewrite a present one")
    p.add_argument("--reset", action="store_true", help="discard operator edits to non-identity fields")
    p.add_argument("--force-new-identity", action="store_true", help="mint a new identity even if one exists (needs --yes)")
    p.add_argument("--check", action="store_true", help="verify the four identity locations; write nothing")
    p.add_argument("--json", action="store_true", help="with --check: one JSON object")
    p.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--yes", action="store_true", help="confirm a destructive step non-interactively")
    p.add_argument("--conf-dir", default=DEFAULT_CONF_DIR)
    p.add_argument("--state-dir", default=DEFAULT_STATE_DIR)
    p.add_argument("--defaults", help="seed file to use instead of the shipped one")
    p.add_argument("--avahi-service", default=None, help="with --check: the live Avahi service file")
    p.add_argument("--lock-file", default=DEFAULT_LOCK)
    p.add_argument("--sysfs", default=DEFAULT_SYSFS, help=argparse.SUPPRESS)
    p.add_argument("--systemctl", default="systemctl", help=argparse.SUPPRESS)
    p.add_argument("--version", action="store_true")
    return p


# -- identity-adjacent derivation (FR-025a) --------------------------------------------


def _read_mac(sysfs: Path, iface: str) -> str | None:
    try:
        raw = (sysfs / iface / "address").read_text().strip().replace(":", "").lower()
    except OSError:
        return None
    if len(raw) != 12 or raw == SENTINEL_MAC:
        return None
    return raw


def _candidate_interfaces(sysfs: Path) -> list[str]:
    try:
        names = sorted(p.name for p in sysfs.iterdir())
    except OSError:
        return []
    out = []
    for name in names:
        if name == "lo" or name.startswith(VIRTUAL_PREFIXES):
            continue
        real = os.path.realpath(sysfs / name)
        if "/virtual/" in real:
            continue
        out.append(name)
    return out


def _derive_mac(sysfs: Path) -> tuple[str, str] | None:
    """``(mac, interface)`` from ``ethernet0``, else the first physical interface."""
    for iface in ["ethernet0", *_candidate_interfaces(sysfs)]:
        mac = _read_mac(sysfs, iface)
        if mac:
            return mac, iface
    return None


def _derive_ip(iface: str | None) -> str:
    if not iface:
        return "0.0.0.0"
    try:
        import struct

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            packed = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack("256s", iface[:15].encode()))
        return socket.inet_ntoa(packed[20:24])
    except (OSError, ValueError):
        return "0.0.0.0"


# -- seed values -----------------------------------------------------------------------


def _seed_tables(defaults: str | None, overlay: str | None, verbose: bool):
    """Merged seed tables and, per overridden key, the overlay file that won."""
    from ..xml import seed_values

    base = seed_values.load_seed_values(Path(defaults)) if defaults else seed_values.load_seed_values()
    seed_values.validate(base)
    if not overlay:
        return base
    overlays = seed_values.load_overlays(Path(overlay))
    merged, provenance = seed_values.merge(base, overlays)
    if verbose:
        for (schema, type_name, name), path in sorted(provenance.items(), key=lambda kv: str(kv[1])):
            print(f"{path}: [{schema}.{type_name}] {name} overrides the upstream default")
    return merged


# -- documents -------------------------------------------------------------------------


def _load_existing(conf: Path, only: tuple[str, ...] = DOCUMENTS) -> dict[str, Any]:
    """Present documents through the strict read path (Unreadable on failure).

    ``only`` narrows the read: under ``--install-missing`` a present sibling is
    never touched (G8), so it is never read either — a stub or garbage there
    must not turn into a class-2 refusal of the documents that *are* absent.
    """
    from ..xml.settings import NetworkMap, ProjectMappings, Settings

    readers = {"settings.xml": Settings, "network_map.xml": NetworkMap, "default_mappings.xml": ProjectMappings}
    existing: dict[str, Any] = {}
    for name, reader in readers.items():
        path = conf / name
        if not path.exists() or name not in only:
            continue
        try:
            existing[name] = reader(str(path)).get_dict()
        except Exception as exc:  # noqa: BLE001 — any read failure is class 2, named
            raise Unreadable(f"{path}: cannot be read ({type(exc).__name__}: {exc})") from exc
    return existing


def _substitute(obj: Any, table: dict[str, str]) -> None:
    """Literal token substitution in every string leaf (design §10.2, FR-026)."""
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if isinstance(value, str):
                new = value
                for old, replacement in table.items():
                    if old in new:
                        new = new.replace(old, replacement)
                if new != value:
                    obj[key] = new
            elif isinstance(value, (dict, list)):
                _substitute(value, table)
    elif isinstance(obj, list):
        for item in obj:
            _substitute(item, table)


def _set_path(obj: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj[part]
    obj[parts[-1]] = value


def _three_way(name: str, computed: dict[str, Any], on_disk: dict[str, Any] | None,
               recorded: dict[str, Any] | None, reset: bool, kept: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Per field: the value to write (FR-027). Appends every kept edit to ``kept``."""
    result = dict(computed)
    if on_disk is None or reset:
        return result
    for path, disk_value in on_disk.items():
        if path in IDENTITY_PATHS or path not in computed:
            continue
        if recorded is not None:
            if path in recorded and recorded[path] == disk_value:
                continue  # unchanged since we wrote it: recompute
            if path not in recorded:
                continue  # new upstream field: computed
        elif disk_value == computed[path]:
            continue
        result[path] = disk_value
        kept.append((name, path, disk_value))
    return result


def _serialize(obj: Any, schema: str) -> bytes:
    from ..errors import SchemaError
    from ..xml.documents import build_tree, iter_schema_errors
    from ..xml.validators import violation_from_schema_error

    tree = build_tree(obj, schema)
    for error in iter_schema_errors(schema, tree):
        raise SchemaError(str(violation_from_schema_error(error)))
    buffer = io.BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def _mode_for(target: Path) -> int:
    try:
        return target.stat().st_mode & 0o777
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o644 & ~umask


def _write_set(conf: Path, payloads: dict[str, bytes]) -> None:
    """All-or-none over ``os.replace`` (research R6): temporaries first, then the
    replaces in order; on failure every already-replaced target is put back."""
    conf.mkdir(parents=True, exist_ok=True)
    previous: dict[str, bytes | None] = {}
    temporaries: dict[str, str] = {}
    try:
        for name, payload in payloads.items():
            target = conf / name
            previous[name] = target.read_bytes() if target.exists() else None
            handle, temporary = tempfile.mkstemp(dir=str(conf), prefix=f".{name}.", suffix=".tmp")
            with os.fdopen(handle, "wb") as out:
                out.write(payload)
            os.chmod(temporary, _mode_for(target))
            temporaries[name] = temporary
        replaced: list[str] = []
        try:
            for name in payloads:
                os.replace(temporaries[name], str(conf / name))
                temporaries.pop(name)
                replaced.append(name)
        except BaseException:
            for name in replaced:  # restore from the in-memory copies, in reverse
                target = conf / name
                if previous[name] is None:
                    target.unlink(missing_ok=True)
                else:
                    handle, temporary = tempfile.mkstemp(dir=str(conf), prefix=f".{name}.", suffix=".tmp")
                    with os.fdopen(handle, "wb") as out:
                        out.write(previous[name])
                    os.chmod(temporary, _mode_for(target))
                    os.replace(temporary, str(target))
            raise
    finally:
        for temporary in temporaries.values():
            try:
                os.unlink(temporary)
            except OSError:
                pass


# -- the run ---------------------------------------------------------------------------


def _resolve_identity(args, existing_settings, sysfs: Path) -> tuple[dict, str | None, dict]:
    """``(identity, interface, previous)`` — previous is the identity on disk (may be sentinel)."""
    from .Uuid import Uuid

    previous = {}
    if existing_settings is not None:
        node = existing_settings["node"]
        previous = {"uuid": str(node.get("uuid") or ""), "mac": str(node.get("mac") or "")}
    real_before = bool(previous.get("uuid")) and previous["uuid"] != SENTINEL

    if args.uuid:
        try:
            uuid = str(Uuid(args.uuid))
        except ValueError as exc:
            raise Refusal(f"--uuid {args.uuid!r} is not a uuid4: {exc}") from exc
    elif real_before and not args.force_new_identity:
        uuid = previous["uuid"]
    elif args.install_missing and existing_settings is not None:
        uuid = previous["uuid"]  # coherent with what settings.xml carries, sentinel included
    else:
        uuid = str(Uuid())

    iface = None
    if args.mac:
        mac = args.mac.replace(":", "").lower()
        if len(mac) != 12 or any(c not in "0123456789abcdef" for c in mac):
            raise Refusal(f"--mac {args.mac!r} is not 12 hex digits")
    elif real_before and previous.get("mac") and previous["mac"] != SENTINEL_MAC and not args.force_new_identity:
        mac = previous["mac"]
    elif args.install_missing and existing_settings is not None and previous.get("mac"):
        mac = previous["mac"]
    else:
        derived = _derive_mac(sysfs)
        if derived is None:
            raise Refusal("no MAC address could be determined (no ethernet0 and no physical interface under "
                          f"{sysfs}); pass --mac — a sentinel MAC on a live node is refused (FR-025a)")
        mac, iface = derived
    if iface is None and not args.mac:
        iface = "ethernet0" if _read_mac(sysfs, "ethernet0") else None
    return {"uuid": uuid, "mac": mac}, iface, previous


def _run(args) -> int:
    from ..xml import make_defaults
    from . import write_record
    from .NodeList import NodeIndex, NodeRole

    conf = Path(args.conf_dir)
    state = Path(args.state_dir)
    sysfs = Path(args.sysfs)

    if args.force_new_identity and not args.yes:
        raise Refusal("--force-new-identity discards this node's identity (it must be re-adopted); confirm with --yes")

    present = tuple(name for name in DOCUMENTS if (conf / name).exists())
    existing = _load_existing(conf, ("settings.xml",) if args.install_missing else DOCUMENTS)
    identity, iface, previous = _resolve_identity(args, existing.get("settings.xml"), sysfs)
    identity_changed = bool(previous.get("uuid")) and previous["uuid"] != identity["uuid"]

    if args.install_missing:
        targets = [name for name in DOCUMENTS if name not in present]
        if not targets:
            print("nothing to do: all three documents are present")
            return 0
    else:
        targets = list(DOCUMENTS)

    tables = _seed_tables(args.defaults, None if args.no_overlay else args.overlay, args.verbose)
    computed = make_defaults.build(tables, identity)
    record = write_record.load(state)
    kept: list[tuple[str, str, Any]] = []
    tokens = {SENTINEL: identity["uuid"], SENTINEL_MAC: identity["mac"]}
    if identity_changed:
        tokens[previous["uuid"]] = identity["uuid"]
        if previous.get("mac") and previous["mac"] != identity["mac"]:
            tokens[previous["mac"]] = identity["mac"]

    # settings.xml — the inner SettingsType; wrapped for saving
    from ..config.settings import CuemsSettingsType

    settings_new = computed["settings.xml"]["Settings"]
    settings_old = existing.get("settings.xml")
    decided = _three_way("settings.xml", write_record.leaves(settings_new), write_record.leaves(settings_old) if settings_old is not None else None,
                         record.fields_of("settings.xml") if record else None, args.reset, kept)
    for path, value in decided.items():
        if path not in IDENTITY_PATHS:
            _set_path(settings_new, path, value)
    settings_new["node"]["uuid"], settings_new["node"]["mac"] = identity["uuid"], identity["mac"]
    documents: dict[str, Any] = {"settings.xml": CuemsSettingsType({"Settings": settings_new})}

    # network_map.xml — existing rows preserved; self row ensured (practice 3, by reference)
    map_new = computed["network_map.xml"]
    self_row = map_new["node_list"][0]["node"]
    self_row["name"] = socket.gethostname()
    self_row["ip"] = _derive_ip(iface)
    map_old = existing.get("network_map.xml")
    if map_old is not None:
        rows = [item["node"] for item in (map_old.get("node_list") or [])]
        for row in rows:
            _substitute(row, {k: v for k, v in tokens.items() if k in (SENTINEL, previous.get("uuid"))})
            if str(row.get("uuid")) == identity["uuid"]:
                row["mac"] = identity["mac"]
        index = NodeIndex({str(r["mac"]): r for r in rows})
        if not index.ensure(self_row):
            mine = next(r for r in rows if str(r.get("uuid")) == identity["uuid"])
            decided = _three_way("network_map.xml", {"self.name": self_row["name"], "self.ip": self_row["ip"]},
                                 {"self.name": mine.get("name"), "self.ip": mine.get("ip")},
                                 record.fields_of("network_map.xml") if record else None, args.reset, kept)
            mine["name"], mine["ip"] = decided["self.name"], decided["self.ip"]
            mine.setdefault("node_role", NodeRole.firstrun)
            self_row = mine
        map_old["node_list"] = [{"node": r} for r in index.values()]
        documents["network_map.xml"] = map_old
    else:
        documents["network_map.xml"] = map_new

    # default_mappings.xml — retires with feature 014
    dm_new = computed["default_mappings.xml"]
    dm_old = existing.get("default_mappings.xml")
    if dm_old is not None:
        _substitute(dm_old, tokens)
        entries = [item["node"] for item in (dm_old.get("nodes") or [])]
        if not any(str(e.get("uuid")) == identity["uuid"] for e in entries):
            dm_old["nodes"] = [*(dm_old.get("nodes") or []), {"node": dm_new["nodes"][0]["node"]}]
        decided = _three_way("default_mappings.xml", write_record.leaves(dm_new), write_record.leaves(dm_old),
                             record.fields_of("default_mappings.xml") if record else None, args.reset, kept)
        for path, value in decided.items():
            _set_path(dm_old, path, value)
        documents["default_mappings.xml"] = dm_old
    else:
        documents["default_mappings.xml"] = dm_new

    for document in documents.values():
        _substitute(document, tokens)

    payloads = {name: _serialize(documents[name], SCHEMA_OF[name]) for name in targets}
    if identity["uuid"] != SENTINEL:
        for name, payload in payloads.items():
            if SENTINEL.encode() in payload or SENTINEL_MAC.encode() in payload:
                raise Refusal(f"{conf / name}: a sentinel token survived specialisation; refusing to write")

    if record is None and any(name in existing for name in targets) and not args.reset:  # noqa: E501
        print(f"{write_record.record_path(state)}: no write record; every on-disk difference is treated as an operator edit")
    for name, path, value in kept:
        print(f"{conf / name}: {MODIFIED_KEPT} {path}={value!r} (run {FIX_RESET} to revert)")
    if args.reset and kept:
        pass
    if args.reset:
        reverted = [(name, path) for name, path in _differences(existing, documents, targets)]
        for name, path in reverted:
            print(f"{conf / name}: reverting {path} to the system default")

    unchanged = [name for name in targets if (conf / name).exists() and (conf / name).read_bytes() == payloads[name]]
    to_write = {name: payloads[name] for name in targets if name not in unchanged}

    if args.dry_run:
        for name in targets:
            print(f"{conf / name}: {'unchanged' if name in unchanged else 'would be written'}")
        return 0

    if to_write:
        try:
            _write_set(conf, to_write)
        except OSError as exc:
            print(f"ERROR: writing {conf}: {exc}; the previous documents were restored", file=sys.stderr)
            return 1
    for name in targets:
        print(f"{conf / name}: {'unchanged' if name in unchanged else 'written'}")

    fields = {
        "settings.xml": write_record.leaves(settings_new),
        "network_map.xml": {"self.uuid": identity["uuid"], "self.mac": identity["mac"],
                            "self.name": str(self_row.get("name")), "self.ip": str(self_row.get("ip"))},
        "default_mappings.xml": write_record.leaves(documents["default_mappings.xml"]),
    }
    new_record = write_record.WriteRecord(write_record.now(), dict(record.documents) if record else {})
    for name in targets:
        new_record.documents[name] = write_record.DocumentRecord(
            str(conf / name), hashlib.sha256(payloads[name]).hexdigest(), fields[name])
    if to_write or record is None:
        write_record.save(state, new_record)

    if identity["uuid"] == SENTINEL:
        print(f"WARNING: this node is {NOT_PROVISIONED} (sentinel identity kept from settings.xml); run: {FIX_PLAIN}", file=sys.stderr)
    if identity_changed or previous.get("uuid") in (None, "", SENTINEL):
        if identity_changed and previous.get("uuid") != SENTINEL:
            print(f"identity changed: {previous['uuid']} -> {identity['uuid']}; this node must be re-adopted")
        print(f"then: {FIX_NODECONF} (the Avahi record is derived from settings.xml by cuems-nodeconf)")
    return 0


def _differences(existing: dict[str, Any], documents: dict[str, Any], targets: list[str]):
    from . import write_record

    for name in targets:
        if name not in existing:
            continue
        old = write_record.leaves(existing[name] if name != "settings.xml" else existing[name])
        new = write_record.leaves(documents[name] if name != "settings.xml" else documents[name]["Settings"])
        for path, value in new.items():
            if path in old and old[path] != value and path not in IDENTITY_PATHS:
                yield name, path


def _nodeconf_active(systemctl: str) -> bool:
    try:
        return subprocess.run([systemctl, "is-active", "--quiet", "cuems-nodeconf.service"],
                              capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.version:
        from .. import __version__

        print(__version__)
        return 0
    if not args.verbose and "CUEMS_LOG_LEVEL" not in os.environ:
        os.environ["CUEMS_LOG_LEVEL"] = "WARNING"  # R15: the library logs to stdout by default

    if args.check:
        from . import identity_check

        report = identity_check.check(Path(args.conf_dir), Path(args.avahi_service) if args.avahi_service else None)
        print(identity_check.render_json(report) if args.json else identity_check.render(report))
        return report.exit_code

    if not args.dry_run and _nodeconf_active(args.systemctl) and not args.yes:
        print("ERROR: cuems-nodeconf.service is active and writes network_map.xml; stop it, or confirm with --yes",
              file=sys.stderr)
        return 1

    lock_path = Path(args.lock_file)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock = open(lock_path, "w")  # noqa: SIM115 — held for the run
    except OSError as exc:
        print(f"ERROR: cannot open lock file {lock_path}: {exc}", file=sys.stderr)
        return 2
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return _run(args)
    except Refusal as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except SeedValueError as exc:  # a bad overlay or seed file: refused before writing
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Unreadable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
