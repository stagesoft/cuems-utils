"""Models for ``settings.xsd`` and ``project_settings.xsd`` (T045).

Eight types, every field set derived from the XSD. Nothing here decides what an
accessor is called or what a value means — that stays in
``tools/ConfigBase.py``, whose names are frozen by FR-018.

Every field defaults to :data:`~cuemsutils.helpers.Unset`: **declared, but not
materialised**. A config object built bare must not start carrying keys its
document never had, because the recorded ``*.config.json`` goldens are the gate
on exactly that (T042, T043a).
"""

from __future__ import annotations

from ..helpers import Unset
from .base import ConfigDict


class PlayerType(ConfigDict):
    """The common shape of the four player sections.

    A real base class rather than four repeated declarations, because the XSD
    says so: ``VideoPlayerType``, ``AudioPlayerType``, ``AudioMixerType`` and
    ``DmxPlayerType`` are ``xs:extension``s of it. ``declared_defaults``
    accumulates across the MRO, so each subclass declares only what it adds and
    the coherence check still sees the full derived set.
    """

    DECLARED_DEFAULTS = {
        "path": Unset,
        "args": Unset,
    }


class VideoPlayerType(PlayerType):
    DECLARED_DEFAULTS = {
        "outputs": Unset,
        "osc_port": Unset,
        "output_latency_ms": Unset,
    }


class AudioPlayerType(PlayerType):
    DECLARED_DEFAULTS = {
        "audio_cards": Unset,
        "output_latency_ms": Unset,
    }


class AudioMixerType(PlayerType):
    """Extends ``PlayerType`` and adds nothing — the XSD extension is empty."""


class DmxPlayerType(PlayerType):
    DECLARED_DEFAULTS = {
        "universes": Unset,
        "output_latency_ms": Unset,
    }


class NodeConfType(ConfigDict):
    """The ``<node>`` section of ``settings.xml`` — ``ConfigBase.node_conf``.

    ``gradient_osc_port`` is declared because the schema requires it. It is
    also the **X13** case: it was added to ``settings.xsd`` as required, which
    invalidated every settings file written before it, including two this
    project shipped. That is recorded as scheduled work under the schema
    evolution convention (T082) and **no ``.xsd`` is edited in this feature**
    (FR-033) — so the field is declared exactly as the schema has it.
    """

    DECLARED_DEFAULTS = {
        "uuid": Unset,
        "mac": Unset,
        "osc_dest_host": Unset,
        "oscquery_ws_port": Unset,
        "oscquery_osc_port": Unset,
        "websocket_port": Unset,
        "load_timeout": Unset,
        "nodeconf_timeout": Unset,
        "discovery_timeout": Unset,
        "mtc_port": Unset,
        "osc_in_port_base": Unset,
        "nng_hub_port": Unset,
        "gradient_osc_port": Unset,
        "videoplayer": Unset,
        "audioplayer": Unset,
        "audiomixer": Unset,
        "dmxplayer": Unset,
    }


class CTimecodeType(ConfigDict):
    """``settings.xsd``'s ``CTimecodeType`` — an ``xs:choice`` of two elements.

    **No element in ``settings.xsd`` references it.** It is declared and
    unreachable, which is why it is modelled rather than left ``GENERIC``: the
    registry requires a binding for every complex type (C7), and the coherence
    test (T041) compares its declared field set against the schema's whether or
    not a document ever produces one. Modelling it costs nothing and keeps
    "every type in the schema is accounted for" true without an exception list.
    """

    DECLARED_DEFAULTS = {
        "CTimecode": Unset,
        "NoneType": Unset,
    }


class SettingsType(ConfigDict):
    """The anonymous ``<Settings>`` element inside ``<CuemsSettings>``.

    This is what ``ConfigBase.settings`` holds and what every scalar accessor
    on ``ConfigBase`` reads through. Bound **by element path**, because the type
    is anonymous — there is no ``SettingsType`` in the schema to bind by name
    (research R3, the same reason ``CuemsScript`` is bound by path).
    """

    DECLARED_DEFAULTS = {
        "conf_path": Unset,
        "library_path": Unset,
        "tmp_path": Unset,
        "database_name": Unset,
        "show_lock_file": Unset,
        "editor_url": Unset,
        "controller_url": Unset,
        "templates_path": Unset,
        "controller_interfaces_template": Unset,
        "node_interfaces_template": Unset,
        "controller_lock_file": Unset,
        "node": Unset,
    }


class CuemsSettingsType(ConfigDict):
    """The document root of ``settings.xml``. One field: ``Settings``."""

    DECLARED_DEFAULTS = {"Settings": Unset}


class SettingType(ConfigDict):
    """``project_settings.xsd``'s ``<setting>`` — a name/value pair.

    The type that makes **compensation #1** deletable. ``load_project_settings``
    used to walk a list of single-key dicts and flatten it into one dict by
    hand, because nothing stated the shape. The shape is stated here.
    """

    DECLARED_DEFAULTS = {
        "name": Unset,
        "value": Unset,
    }


class CuemsProjectSettingsType(ConfigDict):
    """The document root of a project's ``settings.xml``."""

    DECLARED_DEFAULTS = {"setting": Unset}
