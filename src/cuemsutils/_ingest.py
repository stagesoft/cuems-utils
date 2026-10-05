# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The one JSON → ``Mapping`` stage both public ingestions share (T022).

``CuemsScript.from_json`` has accepted three payload forms since feature 006 —
a JSON ``str``, UTF-8 ``bytes``, or an already-decoded ``Mapping`` — and
``ConfigManager.from_json`` is specified as symmetric with it (plan.md §9.3),
*including* those three forms. Writing them a second time would make the
feature that exists to remove a second decoder ship one.

So the stage is factored out rather than copied. What stays at each call site
is the part that genuinely differs: which body shape counts as "a document of
this kind", which ``CuemsScript`` answers from its own class name and the
configuration path answers from its schema's root type.

Private (``_ingest``, like ``_deprecation``) because it is machinery, not
surface: a consumer calls ``from_json`` and catches
:class:`cuemsutils.errors.IngestError`, which **is** public.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from .errors import IngestError


def payload_as_mapping(payload, what: str) -> Mapping:
    """One of the three accepted forms, as a mapping — or ``IngestError``.

    Every refusal here is *"this is not a document of that kind"*, which is why
    they share an exception type distinct from ``SchemaError``: nothing was
    validated, because there was nothing of the right shape to validate.

    ``bytes`` is decoded as UTF-8 **only** and never sniffed for another codec
    (FR-036c) — a guess that succeeds produces a document nobody sent.

    Args:
        payload: a JSON ``str``, UTF-8 ``bytes``, or a ``Mapping``.
        what: how to name the expected thing in a refusal, as it reads in
            *"expected JSON text describing ``{what}``"* — e.g.
            ``"a CuemsScript"`` or ``"a settings document"``.

    Returns:
        Mapping: the payload, decoded if it needed decoding.

    Raises:
        IngestError: the bytes are not UTF-8, the text is not JSON, or the
            result is not a mapping.
    """
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = bytes(payload).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise IngestError(
                f"expected UTF-8 bytes for {what}; the input is not valid "
                f"UTF-8 and no other codec is guessed: {exc}"
            ) from exc

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError as exc:
            raise IngestError(
                f"expected JSON text describing {what}: {exc}"
            ) from exc

    if not isinstance(payload, Mapping):
        raise IngestError(
            f"expected {what} as a mapping, JSON text or UTF-8 bytes; got "
            f"{type(payload).__name__}"
        )

    return payload
