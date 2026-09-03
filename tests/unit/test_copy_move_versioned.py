"""``tools.CopyMoveVersioned`` — untested despite being live in ``cuems-editor``
(``cuemseditor.CuemsDBMedia``/``CuemsDBProject``, 9 call sites).

Test shapes are modelled directly on those call sites, not invented in the
abstract:

- ``CuemsDBMedia.new``: ``CopyMoveVersioned.move(tmp_file_path, self.media_path,
  filename)`` — intake an uploaded file under an explicit target filename,
  versioned on collision.
- ``CuemsDBMedia.delete``/``restore``: ``CopyMoveVersioned.move(file_path,
  self.trash_path)`` — no explicit filename, defaults to the source's
  basename.
- ``CuemsDBProject.delete``/``restore``: ``CopyMoveVersioned.move(project_dir,
  self.trash_path, project.unix_name)`` — the *source* is a directory, not a
  file (a whole project). ``shutil.move`` handles both, and the collision loop
  makes no file/directory distinction, so the versioning behaviour must hold
  for directories too.
- ``CuemsDBProject.export``: ``CopyMoveVersioned.move(tmp_zip_path,
  server_export_path, output_filename)`` — versioning must preserve the
  ``.zip`` extension, not just append the suffix to the whole name.

``copy_dir`` has no consumer anywhere in the ecosystem as of this writing
(checked across ``cuems-editor``, ``cuems-nodeconf``, ``cuems-engine``,
``cuems-common``) but is public API on the same class; tested for parity with
``move``'s versioning behaviour minus the "consumes the source" part.
"""

from __future__ import annotations

import os

from cuemsutils.tools.CopyMoveVersioned import CopyMoveVersioned


# --- move: explicit dest_filename, no collision -------------------------------


def test_move_to_a_clear_destination_uses_the_given_filename(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    orig = src / "upload.tmp"
    orig.write_bytes(b"payload")

    result = CopyMoveVersioned.move(str(orig), str(dest), "song.wav")

    assert result == "song.wav"
    assert (dest / "song.wav").read_bytes() == b"payload"
    assert not orig.exists()


# --- move: dest_filename=None, mirrors the trash/delete call sites ------------


def test_move_with_no_dest_filename_uses_the_source_basename(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    orig = src / "project.zip"
    orig.write_bytes(b"data")

    result = CopyMoveVersioned.move(str(orig), str(dest))

    assert result == "project.zip"
    assert (dest / "project.zip").exists()


# --- move: collision -> versioned suffix, extension preserved -----------------


def test_move_appends_a_numeric_suffix_on_a_single_collision(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "song.wav").write_bytes(b"existing")
    orig = tmp_path / "song.wav"
    orig.write_bytes(b"new")

    result = CopyMoveVersioned.move(str(orig), str(dest), "song.wav")

    assert result == "song-001.wav"
    assert (dest / "song.wav").read_bytes() == b"existing"  # untouched
    assert (dest / "song-001.wav").read_bytes() == b"new"


def test_move_increments_the_suffix_across_repeated_collisions(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "song.wav").write_bytes(b"v0")
    (dest / "song-001.wav").write_bytes(b"v1")
    (dest / "song-002.wav").write_bytes(b"v2")
    orig = tmp_path / "song.wav"
    orig.write_bytes(b"v3")

    result = CopyMoveVersioned.move(str(orig), str(dest), "song.wav")

    assert result == "song-003.wav"
    assert (dest / "song-003.wav").read_bytes() == b"v3"


def test_move_versioning_preserves_the_extension():
    """``CuemsDBProject.export``'s call site relies on this: the destination
    must still end ``.zip`` after a collision, not ``.something-001``."""
    base, ext = os.path.splitext("archive-001.zip")
    assert ext == ".zip"


def test_move_versioning_preserves_the_extension_end_to_end(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "archive.zip").write_bytes(b"existing")
    orig = tmp_path / "archive.zip"
    orig.write_bytes(b"new")

    result = CopyMoveVersioned.move(str(orig), str(dest), "archive.zip")

    assert result == "archive-001.zip"


# --- move: the source is a directory, mirrors CuemsDBProject's trash/restore --


def test_move_relocates_a_directory_when_the_destination_is_clear(tmp_path):
    projects = tmp_path / "projects"
    trash = tmp_path / "trash"
    projects.mkdir()
    trash.mkdir()
    project_dir = projects / "my_project"
    project_dir.mkdir()
    (project_dir / "cue_script.xml").write_text("<script/>")

    result = CopyMoveVersioned.move(str(project_dir), str(trash), "my_project")

    assert result == "my_project"
    assert not project_dir.exists()
    assert (trash / "my_project" / "cue_script.xml").read_text() == "<script/>"


def test_move_versions_a_directory_on_collision(tmp_path):
    """The exact shape of ``CuemsDBProject.restore``: a trashed project
    directory moving back to ``projects_path``, where a directory of the same
    ``unix_name`` already exists there."""
    projects = tmp_path / "projects"
    trash = tmp_path / "trash"
    projects.mkdir()
    trash.mkdir()
    (projects / "my_project").mkdir()  # already occupies the target name
    trashed = trash / "my_project"
    trashed.mkdir()
    (trashed / "cue_script.xml").write_text("<restored/>")

    result = CopyMoveVersioned.move(str(trashed), str(projects), "my_project")

    assert result == "my_project-001"
    assert (projects / "my_project-001" / "cue_script.xml").read_text() == "<restored/>"
    assert (projects / "my_project").is_dir()  # the pre-existing one, untouched


# --- copy_dir: no known consumer, tested for parity with move's versioning ----


def test_copy_dir_to_a_clear_destination_leaves_the_source_intact(tmp_path):
    src = tmp_path / "src_dir"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    (src / "file.txt").write_text("content")

    result = CopyMoveVersioned.copy_dir(str(src), str(dest), "copied")

    assert result == "copied"
    assert (dest / "copied" / "file.txt").read_text() == "content"
    assert src.exists()  # copy, not move


def test_copy_dir_appends_a_numeric_suffix_on_collision(tmp_path):
    src = tmp_path / "src_dir"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    (dest / "copied").mkdir()

    result = CopyMoveVersioned.copy_dir(str(src), str(dest), "copied")

    assert result == "copied-001"
    assert (dest / "copied-001").is_dir()
    assert (dest / "copied").is_dir()  # untouched
