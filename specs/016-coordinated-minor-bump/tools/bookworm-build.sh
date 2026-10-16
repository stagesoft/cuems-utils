#!/bin/bash
# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bookworm-build.sh <repo-path> — build any CUEMS package inside an unprivileged
# bookworm chroot (feature 016, T006; research R7, R15). Generalised from
# cuems-editor/tests/packaging/bookworm-build.sh, which stays as it is.
#
#   mmdebstrap --mode=unshare --variant=apt: a user-namespace chroot built as the
#   calling user and thrown away afterwards (target /dev/null). A host build on a
#   Debian 13 box would target trixie and bake its python3 into the venv.
#
# cuemsutils 0.1.1 exists only as the cuems-utils bump commit, so a wheel is built
# from UTILS (a CLEAN checkout — refused otherwise) and offered to dh-virtualenv's
# pip through PIP_FIND_LINKS. cuems-power-bridge builds its own wheel from a
# sibling path; that path is given inside the chroot as CUEMS_UTILS_SRC.
#
# Interpreter check: cuems-utils keeps pyvenv.cfg in its .deb; the siblings delete
# it (cuems-utils owns /usr/lib/cuems), so for them pass 1 runs the build up to
# override_dh_virtualenv and copies the venv's pyvenv.cfg out first.
#
# Usage:  bookworm-build.sh <repo-path>
# Env:    UTILS=<path>  clean cuems-utils checkout (required)
#         OUT=<file>    evidence file (required; never overwritten — refused if it exists)
#         WORK=<dir>    scratch (default: mktemp)
#         MIRROR=<url>  Debian mirror (default: http://deb.debian.org/debian)
# Exit:   0 only if every expected .deb built, each .deb's Version equals the
#         changelog's, and the venv home is /usr/bin (or the package has no venv).
#         2 on a precondition failure (tool missing, dirty UTILS, OUT exists).

set -euo pipefail

REPO="$(cd "${1:?usage: bookworm-build.sh <repo-path>}" && pwd)"
NAME="$(basename "$REPO")"
: "${UTILS:?UTILS= a clean cuems-utils checkout}"
UTILS="$(cd "$UTILS" && pwd)"
: "${OUT:?OUT= an evidence file}"
WORK="${WORK:-$(mktemp -d -t "016-$NAME-bookworm-XXXXXX")}"
MIRROR="${MIRROR:-http://deb.debian.org/debian}"

log() { printf '[bookworm-build %s] %s\n' "$NAME" "$*" >&2; }

for tool in mmdebstrap newuidmap newgidmap git tar dpkg-parsechangelog dpkg-deb uv; do
    command -v "$tool" >/dev/null 2>&1 || { log "missing required tool: $tool"; exit 2; }
done
grep -q "^$(id -un):" /etc/subuid && grep -q "^$(id -un):" /etc/subgid \
    || { log "no /etc/subuid or /etc/subgid range for $(id -un)"; exit 2; }
[ -n "$(git -C "$UTILS" status --porcelain)" ] && { log "UTILS is not clean: $UTILS"; exit 2; }
[ -e "$OUT" ] && { log "evidence exists, refusing to overwrite: $OUT"; exit 2; }
mkdir -p "$(dirname "$OUT")"

mkdir -p "$WORK"/{wheels,build/src,build/utils}
log "work directory: $WORK"

UTILS_COMMIT="$(git -C "$UTILS" rev-parse HEAD)"
REPO_COMMIT="$(git -C "$REPO" rev-parse HEAD)"
REPO_DIRTY=""
[ -n "$(git -C "$REPO" status --porcelain)" ] && REPO_DIRTY=" (+ uncommitted changes)"

# The cuemsutils wheel (not needed to build cuems-utils itself, harmless there).
(cd "$UTILS" && uv build --wheel --out-dir "$WORK/wheels") > "$WORK/wheel.log" 2>&1 \
    || { log "wheel build failed — see $WORK/wheel.log"; exit 1; }
WHEEL="$(basename "$(ls "$WORK"/wheels/cuemsutils-*.whl | head -1)")"
cp "$WORK/wheels/$WHEEL" "$WORK/build/"

# Sources: tracked + untracked-not-ignored files only (local .venv etc. stay out).
git -C "$REPO" ls-files -co --exclude-standard -z \
    | tar -C "$REPO" --null -T - -cf - | tar -C "$WORK/build/src" -xf -
git -C "$UTILS" ls-files -co --exclude-standard -z \
    | tar -C "$UTILS" --null -T - -cf - | tar -C "$WORK/build/utils" -xf -
VERSION="$(cd "$WORK/build/src" && dpkg-parsechangelog -SVersion)"
PACKAGES="$(awk '/^Package:/{print $2}' "$WORK/build/src/debian/control")"
VENV_PKG=""
if grep -q 'python-virtualenv' "$WORK/build/src/debian/rules"; then
    VENV_PKG="$(echo "$PACKAGES" | head -1)"
fi
log "building $NAME $VERSION from ${REPO_COMMIT:0:7}$REPO_DIRTY; packages: $(echo $PACKAGES); venv package: ${VENV_PKG:-none}"

cat > "$WORK/build/build.sh" <<BUILD
#!/bin/sh
# Runs inside the bookworm chroot.
set -e
export DEBIAN_FRONTEND=noninteractive
B=/tmp/build
mkdir -p \$B/out
apt-get -y --no-install-recommends install \
    dh-virtualenv debhelper dpkg-dev fakeroot build-essential git \
    python3-all python3-dev python3-pip python3-setuptools python3-venv python3-wheel \
    > \$B/out/apt.log 2>&1
apt-get -y --no-install-recommends build-dep \$B/src >> \$B/out/apt.log 2>&1 || true
{
    . /etc/os-release; echo "os: \$PRETTY_NAME"
    echo "python3: \$(command -v python3) -> \$(readlink -f "\$(command -v python3)") \$(python3 --version 2>&1)"
    dpkg-query -W -f='dh-virtualenv \${Version}\n' dh-virtualenv
    dpkg-query -W -f='debhelper \${Version}\n' debhelper
} > \$B/out/versions.txt
cd \$B/src
export PIP_FIND_LINKS=\$B PIP_DISABLE_PIP_VERSION_CHECK=1 CUEMS_UTILS_SRC=\$B/utils
if [ -n "$VENV_PKG" ]; then
    ( fakeroot debian/rules build \
      && fakeroot debian/rules override_dh_virtualenv \
      && cp debian/$VENV_PKG/usr/lib/cuems/pyvenv.cfg \$B/out/pyvenv.cfg ) > \$B/out/pass1.log 2>&1 \
      && echo "pass1 OK" >> \$B/out/result.txt || echo "pass1 FAILED" >> \$B/out/result.txt
    fakeroot debian/rules clean > \$B/out/clean.log 2>&1 || true
fi
dpkg-buildpackage -b -us -uc -rfakeroot > \$B/out/build.log 2>&1 \
  && echo "build OK" >> \$B/out/result.txt || echo "build FAILED" >> \$B/out/result.txt
cp \$B/*.deb \$B/out/ 2>/dev/null || true
exit 0
BUILD

mmdebstrap --mode=unshare --variant=apt --include=ca-certificates \
    --customize-hook='mkdir -p "$1/tmp/build"' \
    --customize-hook="copy-in $WORK/build/src $WORK/build/utils $WORK/build/$WHEEL $WORK/build/build.sh /tmp/build" \
    --customize-hook='chroot "$1" sh /tmp/build/build.sh' \
    --customize-hook="copy-out /tmp/build/out $WORK/build" \
    bookworm /dev/null "$MIRROR" > "$WORK/build/mmdebstrap.log" 2>&1 \
    || { log "build chroot failed — see $WORK/build/mmdebstrap.log"; exit 1; }

R="$WORK/build/out"
FAIL=""
{
    echo "# 016 bookworm build — $NAME (mmdebstrap --mode=unshare; tools/bookworm-build.sh)"
    echo "date: $(date -Iseconds)"
    echo "host: $(. /etc/os-release; echo "$PRETTY_NAME"), mmdebstrap $(mmdebstrap --version 2>/dev/null | awk '{print $2}')"
    echo "repo: $NAME @ $REPO_COMMIT$REPO_DIRTY, changelog version $VERSION"
    echo "cuemsutils wheel: $WHEEL from $UTILS @ $UTILS_COMMIT (clean)"
    echo
    echo "## chroot"; cat "$R/versions.txt" 2>/dev/null || echo "(no versions.txt)"
    echo; echo "## result"; cat "$R/result.txt" 2>/dev/null || echo "(no result.txt)"
    echo; echo "## packages"
    for p in $PACKAGES; do
        DEB="$(ls "$R"/"$p"_"$VERSION"_*.deb 2>/dev/null | head -1 || true)"
        if [ -z "$DEB" ]; then echo "$p: MISSING"; FAIL="$FAIL missing:$p"; continue; fi
        V="$(dpkg-deb -f "$DEB" Version)"
        echo "$(basename "$DEB")  sha256 $(sha256sum "$DEB" | cut -d' ' -f1)"
        dpkg-deb -f "$DEB" Package Version Architecture Depends Breaks | sed 's/^/  /'
        [ "$V" = "$VERSION" ] || { echo "  VERSION MISMATCH: deb $V != changelog $VERSION"; FAIL="$FAIL version:$p"; }
    done
    echo; echo "## venv interpreter"
    if [ -z "$VENV_PKG" ]; then
        echo "no venv (package does not use dh-virtualenv)"
    else
        if [ -f "$R/pyvenv.cfg" ]; then HOME_LINE="$(grep -E '^home *=' "$R/pyvenv.cfg")"
        else
            DEB="$(ls "$R"/"$VENV_PKG"_"$VERSION"_*.deb 2>/dev/null | head -1 || true)"
            HOME_LINE="$( [ -n "$DEB" ] && dpkg-deb --fsys-tarfile "$DEB" | tar -xO ./usr/lib/cuems/pyvenv.cfg 2>/dev/null | grep -E '^home *=' || echo 'home = <missing>')"
        fi
        echo "pyvenv.cfg: $HOME_LINE"
        echo "$HOME_LINE" | grep -qE '^home *= */usr/bin$' || FAIL="$FAIL home"
    fi
    if [ -n "$FAIL" ]; then echo; echo "### tail of build.log"; tail -40 "$R/build.log" 2>/dev/null || true; fi
    echo; echo "## verdict: ${FAIL:-OK}"
} > "$OUT"

log "evidence: $OUT"
[ -z "$FAIL" ] || { log "FAILED:$FAIL"; exit 1; }
log "OK"
