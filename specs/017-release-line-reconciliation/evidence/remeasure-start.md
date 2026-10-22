# Re-measure at implementation start (T002)

Measured 2026-10-21T17:28:16Z on `cb4dad3` after `git fetch --all --tags --prune`.

## Refs

```
HEAD                                     cb4dad3
origin/debian/bookworm                   398a9cf
origin/main                              23e4752
origin/feat/xml-refactor                 2318dee
xml-refactor-merge-candidate^{commit}    4b336cd
HEAD..origin/debian/bookworm  77
HEAD..origin/main             11
main...bookworm (left right)  1	67
merge-base                    07a7f9f
newest tags: xml-refactor-merge-candidate debian/0.1.0rc17 v0.1.0rc17 debian/0.1.0rc16+1 debian/0.1.0rc16 
```

## main vs bookworm content (src tests CHANGELOG.md)

```
(empty above = identical)
```

## Conflict set (merge-tree)

```
CHANGELOG.md
debian/README.Debian
debian/changelog
debian/control
debian/rules
src/cuemsutils/__init__.py
src/cuemsutils/cues/ActionCue.py
src/cuemsutils/cues/CueList.py
src/cuemsutils/cues/CuemsScript.py
src/cuemsutils/cues/MediaCue.py
src/cuemsutils/xml/schemas/script.xsd

```

## Modify/delete risk (deleted on HEAD ∩ modified on bookworm since merge-base)

```
(empty above = none)
```

## Added on bookworm since merge-base (excluding specs/)

```
52
```

## Stray sweep (refs with commits on neither line)

```
1 refs/remotes/origin/feat/faders
1 refs/remotes/origin/gh-pages
1 refs/remotes/origin/options
1 refs/remotes/origin/parser-fixxes
1 refs/tags/v0.0.9rc7
```

## Released Debian headers (bookworm, non-UNRELEASED)

```
0.1.0rc17 0.1.0rc16+1 0.1.0rc16 0.1.0rc15 0.1.0rc14 0.1.0rc12 0.1.0rc11 0.1.0rc10 0.1.0rc9 0.1.0rc8 
```

## PyPI 0.1.0 releases (JSON API, yanked included)

```
['0.1.0rc1', '0.1.0rc2', '0.1.0rc3', '0.1.0rc4', '0.1.0rc7', '0.1.0rc8', '0.1.0rc10', '0.1.0rc11', '0.1.0rc14', '0.1.0rc15', '0.1.0rc16']
```

## R17 comparison

```
added since merge-base: 52 = 42 strays (research R17) + 10 kept additions, exact match (diff empty).
All seven kept debian/ files exist on HEAD (add/add merges, not new files).
```

**Verdict: snapshot holds; no stop (FR-004).**
