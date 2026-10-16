<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — a candidate-tag message

One plain-text file per repository at `../.xml-refactor-tag-messages/<repo>.txt` (relative to
this repository; absolute `/disk/Projects/StageLab/.xml-refactor-tag-messages/`). It is read
by the maintainer and applied with:

```bash
git -C ../<repo> tag -s -f -a xml-refactor-merge-candidate -F ../.xml-refactor-tag-messages/<repo>.txt <commit>
```

This feature writes the files. **It never runs that command.**

## Required content, in this order

1. **Subject line**: `xml-refactor merge candidate — <package> <target version>`.
2. **Relocation line**, only for a repository that has a tag today (`cuems-common`,
   `cuems-nodeconf`, `cuems-power-bridge`, `cuems-frontend`): `RELOCATED from <old tag commit>
   (<date>)`, with the reason, which is the coordinated minor bump. Use the tag's **commit**
   (`git rev-parse <tag>^{commit}`), never the tag object.
3. **Commit to tag**: the full 40-character hash, on a line of its own, `Tag: <hash>`. For
   `cuems-utils` this is the head of its `feat/xml-refactor` after 016's merge (spec FR-016, as
   amended 2026-10-16; originally the record commit), followed by `Branch: 016-coordinated-minor-bump (not yet merged into
   feat/xml-refactor)` and `Bump commit: <hash>` for reference.
4. **Version**: the target, and every self-version site that states it.
5. **What the bump changed**: the relation-matrix rows this repository owns, old → new.
6. **Carries**: what the candidate contains since its previous tag, or since the branch point for a
   first tag. Keep the existing message's narrative and update it; do not discard it.
7. **Pairs with**: every counterpart as `<repo> <version> at <commit>`. Each named commit MUST be
   the commit in that repository's own message (the set composes).
8. **Release-line reconciliation** (FR-010): `NOT YET RECONCILED with <line> — <N> commits behind
   at <start>, <M> at <bump>; absent released entries: <list>`. Then the sentence *"Do not publish
   until reconciled; re-verify this repository's relations after the merge."* For `cuems-nodeconf`
   (0 behind), state that it is reconciled. For `cuems-engine`, state the FR-010a re-measurement.
9. **Named content gaps**, where they apply: `cuems-utils` and `cuems-engine` name
   `stop_project` (rc17 / rc6-5, research R3); `cuems-utils` and `cuems-power-bridge` name
   `CACHEDIR.TAG` (planning document §10.2).
10. **Evidence**: suite results in both arms, with the interpreter path; build result; install
    demonstration result (where one exists); the path of the evidence in
    `cuems-utils/specs/016-coordinated-minor-bump/evidence/<repo>/`.
11. **Validation status**: *"Not validated on re-cut tags. Planning document rule 5 / §11 step 9 runs
    after the maintainer re-cuts."* Hardware verification ledgers the old message names are carried
    over.

## Verification (run by the task that writes the file, and again before `cuems-utils`' message)

- The `Tag:` hash exists and equals `git -C <repo> rev-parse feat/xml-refactor` (for `cuems-utils`:
  the same: `git rev-parse feat/xml-refactor`, after 016's merge).
- The version in the subject equals the changelog head at that commit (`package.json` for
  `cuems-frontend`).
- Every `Pairs with` commit equals the `Tag:` hash in that repository's file.
- After any amend (FR-021), the file is regenerated and the check runs again.

## The folder's README

`../.xml-refactor-tag-messages/README.md`: the application order (`cuems-common`, `cuems-nodeconf`,
`cuems-power-bridge`, `cuems-engine`, `cuems-editor`, `cuems-frontend`, `cuems-utils` last), the
apply command above, the post-apply check `git rev-parse <tag>^{commit}`, and the reminder that
pushing tags is a separate, maintainer-only act.
