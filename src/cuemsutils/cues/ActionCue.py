# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
from ..helpers import ensure_items
from .Cue import Cue

REQ_ITEMS = {
    'action_target': None,
    'action_type': 'play'
}

#: Action types that act on the whole loaded project and take no target
#: (feature 017, A-1). Consulted by three T2 rules — ``action_target_required``
#: (passes ``None``), ``action_target_resolves`` (skips), and
#: ``project_action_takes_no_target`` (repairs a leftover target to ``None``) —
#: and by ``ActionCue.__init__`` / ``set_action_target`` (``from_json`` reaches
#: those two). Adding a value is a one-line change here plus its own test.
TARGETLESS_ACTION_TYPES: frozenset[str] = frozenset({'stop_project'})


class ActionCue(Cue):
    """A cue that represents an action to be performed on a target object.

    This cue is used to trigger actions on other objects in the system, such as
    playing, pausing, or stopping media cues (``action_target`` is that cue's
    uuid).

    Project-scope actions act on the whole loaded project and take no target:
    the types in :data:`TARGETLESS_ACTION_TYPES`. The one there is
    ``stop_project``, the authored end of an unattended show, which the engine
    turns into its own STOP (running = no, every cue reset, nodes re-armed).
    Its ``action_target`` is ``None`` (an empty string is coerced to ``None``),
    and it is written ``<action_target />``, which the XSD ``TargetType``
    allows.
    - **Construction** and the **setter** accept ``None`` for it. That is what
      the frontend sends, and it reaches the constructor through ``from_json``.
    - A **leftover target** (a uuid kept when a ``stop`` cue was retyped) is
      refused on ``save`` by the T2 rule ``project_action_takes_no_target``, and
      repaired to ``None`` on load, with the repair reported.

    Every other action type still requires a target, and refuses ``None`` at
    construction, at the setter, and at save and load (``action_target_required``).

    ``pause_project``/``resume_project`` are **not** action types: project
    pause/resume is deferred, and the handover is
    ``specs/planning/project-pause-resume-deferred.md``.
    """

    #: Declared fields and their defaults for this class alone;
    #: :meth:`CuemsDict.declared_defaults` accumulates the chain.
    DECLARED_DEFAULTS = REQ_ITEMS

    #: T015. ``_initialized`` (below) is deliberately **not** here — it is
    #: the named exception the runtime hook must never touch; see
    #: ``CuemsDict._init_runtime``'s docstring.
    RUNTIME_FIELDS = {
        '_action_target_object': None,
    }

    def __init__(self, init_dict: dict = None):
        """Initialize an ActionCue.

        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values from REQ_ITEMS will be used.

        Raises:
            ValueError: If init_dict explicitly sets action_target to None for
                an action type that needs a target (any type outside
                :data:`TARGETLESS_ACTION_TYPES`).
        """
        self._initialized = False
        if init_dict:
            # The type is read from init_dict, not from self: population order
            # is not guaranteed, so the type may not be set yet.
            if ('action_target' in init_dict and init_dict['action_target'] is None
                    and init_dict.get('action_type') not in TARGETLESS_ACTION_TYPES):
                raise ValueError('action_target is required')
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        else:
            init_dict = REQ_ITEMS
        super().__init__(init_dict)
        # Not part of ``_init_runtime()``: this flag gates ``set_action_target``
        # below, so it must go true only *after* population. See the hook's
        # docstring in ``helpers.py``.
        self._initialized = True

    def get_action_target(self):
        """Get the target object for the action.

        Returns:
            The target object identifier.
        """
        return super().__getitem__('action_target')

    def set_action_target(self, action_target: str) -> None:
        """Set the target object for the action.

        Args:
            action_target: The target object identifier.

        Raises:
            ValueError: If action_target is None after initialisation is
                complete and the action type needs a target.
                ``action_target_required`` decides, and it passes ``None`` for
                a type in :data:`TARGETLESS_ACTION_TYPES`.
        """
        # Delegates to the named rule; the **gate stays here** (T073, T074).
        # ``_initialized`` is what holds the rule off during population, and
        # moving the rule body does not move the gate: with it open on decode,
        # fourteen setters would gain new reach on the read path, which FR-026
        # forbids.
        # Delegates to the named rule; the **gate stays here** (T073, T074).
        # ``_initialized`` is what holds the rule off during population, and
        # moving a rule *body* never moves its gate: with the gate open on
        # decode, fourteen setters would gain new reach on the read path, which
        # FR-026 forbids.
        #
        # Imported inside the function on purpose — ``cuemsutils.xml``'s
        # package ``__init__`` imports ``cues``, so a module-scope import here
        # closes the cycle the package is arranged to keep open.
        from ..xml.validators import enforce

        if getattr(self, '_initialized', False):
            enforce('action_target_required', action_target, self)
        super().__setitem__(
            'action_target', self.coerce('action_target', action_target)
        )

    action_target = property(get_action_target, set_action_target)

    def get_action_type(self) -> str:
        """Get the type of action to perform.

        Returns:
            str: The action type (e.g., 'play', 'pause', 'stop').
        """
        return super().__getitem__('action_type')

    def set_action_type(self, action_type: str) -> None:
        """Set the type of action to perform.

        Args:
            action_type (str): The action type (e.g., 'play', 'pause', 'stop').
        """
        super().__setitem__('action_type', action_type)

    action_type = property(get_action_type, set_action_type)

