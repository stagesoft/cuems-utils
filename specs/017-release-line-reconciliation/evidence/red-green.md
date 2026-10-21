# Red → green pairs (FR-080, SC-TEST-001)

Columns follow data-model §5. `held` means the check was already green on its base. That is
recorded, not counted as a red→green pair, and never given an invented red (research R7).

## A-1 + A-2d + Q13 retirement (T018–T022 red on M3 `97ee1f9`; green in T030)

Red run: `pytest tests/unit/test_targetless_actions.py tests/integration/test_rc17_migration.py
tests/contract/test_retired_action_types.py tests/unit/test_descriptor_repairability_order.py`
on M3, with **no source change**: **18 failed, 14 passed**.

| Test | On M3 | Why |
|---|---|---|
| `test_row1_stop_project_constructs_without_a_target` | held | |
| `test_row3_an_empty_target_is_stored_as_none` | held | |
| `test_row4_from_json_accepts_a_null_target` | held | |
| `test_row8_stop_project_constructs_with_a_target` | held | |
| `test_row9_a_stop_cue_without_a_target_is_still_refused_at_construction` | held | |
| `test_row10_a_stop_cue_without_a_target_is_refused_at_save` | held | |
| `test_row10_a_stop_cue_without_a_target_is_refused_at_load_and_never_retyped` | held | |
| `test_changing_the_type_away_from_stop_project_is_caught_at_save` | held | |
| `test_row12_an_unknown_action_type_is_refused_by_t1_at_save` | held | |
| `test_row12_an_unknown_action_type_is_refused_by_t1_at_load` | held | |
| `test_the_rc17_control_document_loads_clean_after_migration` | held | |
| `test_rc17s_stored_media_values_survive_the_migration[stop_control.xml]` | held | |
| `test_action_target_is_published_unrepairable` | held | |
| `test_the_map_is_the_same_whatever_order_the_rules_are_registered_in` | held | |
| `test_row2_stop_project_constructs_with_a_none_target` | **red** | |
| `test_the_setter_accepts_none_on_a_stop_project_cue` | **red** | |
| `test_row5_save_writes_an_empty_target_element` | **red** | |
| `test_row6_the_saved_document_loads_clean` | **red** | |
| `test_row7_a_leftover_target_is_repaired_to_none_on_load[resolving]` | **red** | |
| `test_row7_a_leftover_target_is_repaired_to_none_on_load[dangling]` | **red** | |
| `test_row8a_save_refuses_a_leftover_target_with_an_actionable_message` | **red** | |
| `test_row8b_validate_reports_it_and_changes_nothing` | **red** | |
| `test_the_rc17_stop_project_document_loads_clean_after_migration` | **red** | |
| `test_rc17s_stored_media_values_survive_the_migration[stop_project.xml]` | **red** | |
| `test_a_retired_value_is_refused_by_t1_at_save[pause_project]` | **red** | |
| `test_a_retired_value_is_refused_by_t1_at_save[resume_project]` | **red** | |
| `test_a_retired_value_is_refused_by_t1_at_load[pause_project]` | **red** | |
| `test_a_retired_value_is_refused_by_t1_at_load[resume_project]` | **red** | |
| `test_a_retired_value_from_json_is_refused_where_a_document_would_be[pause_project]` | **red** | |
| `test_a_retired_value_from_json_is_refused_where_a_document_would_be[resume_project]` | **red** | |
| `test_the_descriptor_does_not_publish_a_retired_value` | **red** | |
| `test_the_schema_does_not_enumerate_a_retired_value` | **red** | |

**The 14 `held`:**
- Constructing `stop_project` with no target, with `""` or with a uuid already worked (rows 1, 3, 8), and so did `from_json` without a `None` (row 4).
- The negative twins (rows 9, 10, 12, and retyping caught at save) already hold, and are kept as guards.
- The rc17 **control** document already migrated CLEAN, with its media values intact.
- Both descriptor checks hold on M3: `action_target` is UNREPAIRABLE, and the map's order makes no difference while no field has disagreeing rules. They become meaningful once the repairable rule exists (FR-023a). Before then they are pins, not reds.

**The 18 red**, for the intended reasons:
- `None` refused at construction and setter (S-2);
- save and load refused by T2 `action_target_required` (S-1, S-1′, the rc17 fixture);
- a leftover target loads CLEAN instead of REPAIRED (row 7, both variants);
- save does not refuse a leftover target (row 8a), and `validate()` does not report it (row 8b);
- `pause_project`/`resume_project` are still accepted and published (Q13).

**Test bug found and fixed while recording the reds:** row 7's dangling variant first used a
stdlib `uuid.UUID` object. The writer serialises that as child elements, so it failed **T1**
instead of the intended reason. It is now a uuid4 *string*, as a document carries one.

### Green, on A-1's commit `3a02272`

The same four files: **32 passed, 0 failed**.

Full suite on `3a02272`, in the real checkout beside the siblings: **3883 passed, 13 failed, 112
skipped, 2 xfailed**. The 13 are all accounted for:
- **7 pre-existing**, identical to arm A beside the siblings (`suite-A-1b.md`):
  `test_migration_guide::test_the_coupled_engine_version_resolves` and six
  `test_release_matrix::test_siblings_at_their_candidate_tags[*]`, which are `XPASS(strict)`
  since the 016 re-cut.
- **6 owned by US2**, red since M1:
  - A-2a `test_action_type_enumerates_exactly_twelve_values` and A-2b
    `test_the_descriptor_publishes_exactly_those_twelve_values` (T036);
  - A-2c `test_enum_audit` (T036);
  - rc17's `test_constructor_accepts_an_empty_target_and_refuses_none` (A-3a) and
    `test_setter_still_refuses_none_after_init`. Both are contradicted by A-1, which accepts
    `None` for `stop_project` (S-2), and both are ported or retired in T037;
  - rc15's `TestFileMd5::test_stored_lowercase` (A-4, retired in T040).
- **A-2d fixed**: `test_every_schema_matches_its_recorded_hash` is green.

**One existing contract test updated, not retired:** `tests/contract/test_dangling_reference_rule.py`.
`test_both_reference_rules_are_registered_with_the_right_repairability` asserted that *no* rule on
`action_target` is repairable. It went red on A-1's working tree, because the new repairable rule
exists. Its reasoning still holds for the two **reference** rules (for an action that needs a
target, repairing to `None` restates the violation), so it now asserts exactly that. It names
`project_action_takes_no_target` as the one sanctioned repairable rule, where `None` is the valid
value. The field stays published UNREPAIRABLE (FR-023a).

ruff: **0**. Goldens: `git diff --stat -- tests/golden` **empty**.
