# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_image_builder.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import hashlib
import http.server
import json
import lzma
import shutil
import threading
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import image_builder as image_builder_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.image_builder import (
    DEFAULT_PROJECT_TIMEOUT_SECONDS,
    BaseImageSource,
    BuildProgress,
    ImageBuildError,
    PlatformCheck,
    _hash_directory_tree,
    _install_one_project,
    _read_real_installed_version,
    _remote_content_length,
    _require_free_space,
    _xz_uncompressed_size,
    build_image,
    fetch_base_image,
    fetch_reference_sha256,
    scan_for_leaked_secrets,
    verify_installed_resources,
)


class _FixtureHandler(http.server.BaseHTTPRequestHandler):
    """Serves a real, tiny fixture image and its own real .sha256 sidecar
    from a real local HTTP server - a real end-to-end download+verify
    round trip, no network mocking."""

    image_bytes = b"not a real raspios image, just fixture bytes for the test"

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib method name
        if self.path == "/image.img":
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.image_bytes)))
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        if self.path == "/image.img":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.image_bytes)
        elif self.path == "/image.img.sha256":
            digest = hashlib.sha256(self.image_bytes).hexdigest()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{digest}  image.img\n".encode("utf-8"))
        elif self.path == "/missing-sidecar.img.sha256":
            self.send_response(404)
            self.end_headers()
        elif self.path == "/garbage-sidecar.img.sha256":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not a real hash at all\n")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - silence test output
        pass


@pytest.fixture()
def fixture_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def test_fetch_reference_sha256_parses_a_real_sidecar(fixture_server: str) -> None:
    digest = fetch_reference_sha256(f"{fixture_server}/image.img")
    assert digest == hashlib.sha256(_FixtureHandler.image_bytes).hexdigest()


def test_fetch_reference_sha256_raises_on_missing_sidecar(fixture_server: str) -> None:
    with pytest.raises(ImageBuildError, match="could not fetch"):
        fetch_reference_sha256(f"{fixture_server}/missing-sidecar.img")


def test_fetch_reference_sha256_raises_on_garbage_content(fixture_server: str) -> None:
    with pytest.raises(ImageBuildError, match="did not contain a real"):
        fetch_reference_sha256(f"{fixture_server}/garbage-sidecar.img")


def test_fetch_base_image_verifies_against_the_real_sidecar_when_pinned_hash_is_empty(
    fixture_server: str, tmp_path: Path
) -> None:
    # Real bug this covers: BaseImageSource.sha256 == "" used to make the
    # OLD verification check (`if source.sha256 and ...`) skip entirely -
    # this must now actually fetch and check against the real sidecar.
    source = BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256="")
    dest = fetch_base_image(source, tmp_path)
    assert dest.read_bytes() == _FixtureHandler.image_bytes
    assert not (tmp_path / "image.img.part").exists()


def test_fetch_base_image_rejects_a_tampered_download(fixture_server: str, tmp_path: Path) -> None:
    source = BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256="0" * 64)
    with pytest.raises(ImageBuildError, match="checksum mismatch"):
        fetch_base_image(source, tmp_path)
    # A failed verification must never leave a partial/tampered file behind.
    assert not (tmp_path / "image.img").exists()
    assert not (tmp_path / "image.img.part").exists()


# =============================================================================
# Real pre-flight disk-space checks - added after a real live failure this
# session: a remote CM5 build ran out of space mid-decompression with only
# a bare `xz: ... Write error: No space left on device` deep in a
# traceback. See _require_free_space's own docstring for the full story.
# =============================================================================


def test_require_free_space_passes_when_there_is_real_room(tmp_path: Path) -> None:
    _require_free_space(tmp_path, required_bytes=1024, purpose="a tiny real amount")


def test_require_free_space_raises_with_real_numbers_when_insufficient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_usage = shutil.disk_usage(tmp_path)._replace(free=10 * 1024 * 1024)  # 10 MB free, real type
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: fake_usage)
    with pytest.raises(ImageBuildError, match="not enough free disk space") as excinfo:
        _require_free_space(tmp_path, required_bytes=5 * 1024 * 1024 * 1024, purpose="decompressing a real image")
    # The message must carry real, actionable numbers, not just say "no space".
    assert "decompressing a real image" in str(excinfo.value)
    assert "0.01 GB available" in str(excinfo.value)


def test_remote_content_length_returns_the_real_advertised_size(fixture_server: str) -> None:
    length = _remote_content_length(f"{fixture_server}/image.img")
    assert length == len(_FixtureHandler.image_bytes)


def test_remote_content_length_returns_none_when_the_server_gives_no_real_answer(fixture_server: str) -> None:
    assert _remote_content_length(f"{fixture_server}/missing-sidecar.img") is None
    assert _remote_content_length("http://127.0.0.1:1/unreachable") is None


@pytest.mark.skipif(shutil.which("xz") is None, reason="needs the real xz CLI on PATH")
def test_xz_uncompressed_size_reads_the_real_value_from_the_container(tmp_path: Path) -> None:
    real_payload = b"real bytes, not a guess" * 1000
    xz_path = tmp_path / "fixture.img.xz"
    with lzma.open(xz_path, "wb") as f:
        f.write(real_payload)
    assert _xz_uncompressed_size(xz_path) == len(real_payload)


@pytest.mark.skipif(shutil.which("xz") is None, reason="needs the real xz CLI on PATH")
def test_xz_uncompressed_size_returns_none_for_a_file_that_is_not_real_xz(tmp_path: Path) -> None:
    not_xz = tmp_path / "not-really.xz"
    not_xz.write_bytes(b"just some real bytes, no xz header at all")
    assert _xz_uncompressed_size(not_xz) is None


# =============================================================================
# (P1):
# _install_one_project() must refuse an unpinned entry, clone+checkout by
# real commit SHA (not a mutable branch), and report the REAL post-build
# version from the rootfs's own manifest - never the plan's stale one.
# =============================================================================


def _entry(**overrides) -> EcosystemPlanEntry:
    base = dict(
        name="HYDRA-UMC-SERVER",
        version="0.4.8",
        role="api",
        stack="node",
        git_url="https://github.com/JuanenRac/HYDRA-UMC-SERVER.git",
        commit_sha="c" * 40,
    )
    base.update(overrides)
    return EcosystemPlanEntry(**base)


def test_install_one_project_refuses_an_entry_with_no_resolved_commit_sha(tmp_path: Path) -> None:
    with pytest.raises(ImageBuildError, match="no real, resolved commit SHA"):
        _install_one_project(_entry(commit_sha=None), tmp_path)


def _fake_run_for_install(
    tmp_path: Path,
    *,
    post_build_version: str,
    pre_build_version: str = "0.4.8",
    restore_succeeds: bool = True,
):
    """Simulates a real checkout + build.sh + restore sequence.

    `restore_succeeds` models `git checkout -- .` actually reverting the
    tracked manifest back to `pre_build_version` (the ordinary, expected
    case - a plain working-tree edit is exactly what `git checkout --.`
    reverts) - set False to simulate the one case this project's own
    safety net still exists for: the version living somewhere that
    checkout call cannot reach.
    """
    calls: list[list[str]] = []
    target = tmp_path / "opt" / "hydra-umc" / "hydra-umc-server"

    def fake_run(*command: str, **kwargs):
        calls.append(list(command))
        if command[:2] == ("git", "clone"):
            target.mkdir(parents=True)
            (target / "build.sh").write_text("#!/bin/bash\necho building\n", encoding="utf-8")
            (target / "hydra-umc.project.json").write_text(json.dumps({"version": pre_build_version}), encoding="utf-8")
        elif command[0] == "chroot":
            # Real build.sh behavior this ecosystem's own convention
            # always includes: bump the version as the build's own first
            # real effect - simulated here as whatever the test asks for.
            (target / "hydra-umc.project.json").write_text(json.dumps({"version": post_build_version}), encoding="utf-8")
        elif command[:4] == ("git", "-C", str(target), "checkout") and command[-2:] == ("--", "."):
            if restore_succeeds:
                (target / "hydra-umc.project.json").write_text(json.dumps({"version": pre_build_version}), encoding="utf-8")
        return object()

    return fake_run, calls, target


def test_install_one_project_clones_and_checks_out_the_real_pinned_sha_when_the_version_matches_the_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run, calls, target = _fake_run_for_install(tmp_path, pre_build_version="0.4.8", post_build_version="0.4.8")
    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    real_version = _install_one_project(_entry(commit_sha="c" * 40, version="0.4.8"), tmp_path)

    assert real_version == "0.4.8"
    assert calls[0] == ["git", "clone", "https://github.com/JuanenRac/HYDRA-UMC-SERVER.git", str(target)]
    assert calls[1] == ["git", "-C", str(target), "checkout", "c" * 40]
    assert "--depth" not in calls[0], "a shallow clone cannot check out an arbitrary historical commit"


def test_install_one_project_restores_the_planned_version_after_a_real_incremental_build_regression_for_v07_013(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # (P1 - closing
    # this project's own documented "real, separate future work" gap): build.sh
    # is this ecosystem's own real, INCREMENTAL, version-bumping build
    # script - it ALWAYS advances the version as its own first real
    # effect on every real invocation, exactly what this test simulates.
    # refused on that divergence outright, which meant this
    # pipeline could never actually finish installing a single real
    # project. The real fix restores the pinned commit's tracked files
    # (`git checkout -- .`) right after build.sh's real work is done, so
    # the ordinary case - a normal incremental build.sh - now succeeds,
    # reporting the ORIGINAL planned version, not the bumped one.
    fake_run, calls, target = _fake_run_for_install(tmp_path, pre_build_version="0.4.8", post_build_version="0.4.9")
    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    real_version = _install_one_project(_entry(commit_sha="c" * 40, version="0.4.8"), tmp_path)

    assert real_version == "0.4.8"
    assert calls[-1] == ["git", "-C", str(target), "checkout", "--", "."]


def test_install_one_project_still_refuses_when_the_version_stays_diverged_after_the_restore_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The real safety net keeps, not removes: a version that
    # somehow stays diverged even after `git checkout -- .` (e.g. it
    # lives in a path that checkout call cannot reach) must still refuse
    # to install, exactly like this project's own original closure criterion -
    # only the ordinary, always-diverges-then-restores case above is
    # fixed, not this check itself.
    fake_run, _calls, _target = _fake_run_for_install(
        tmp_path, pre_build_version="0.4.8", post_build_version="0.4.9", restore_succeeds=False
    )
    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    with pytest.raises(ImageBuildError, match="diverged"):
        _install_one_project(_entry(commit_sha="c" * 40, version="0.4.8"), tmp_path)


# =============================================================================
# ("Verificacion del contenido distribuido fuera del checkout"): a
# real, human-curated resource inventory per profile, checked against the
# actual post-build tree - never rescued by a residual file elsewhere.
# =============================================================================


def test_verify_installed_resources_reports_nothing_missing_when_everything_is_present(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    missing = verify_installed_resources(tmp_path, ("dist/index.html",))
    assert missing == ()


def test_verify_installed_resources_reports_every_real_missing_path(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    missing = verify_installed_resources(tmp_path, ("dist/index.html", "dist/bundle.js", "server/main.py"))
    assert missing == ("dist/bundle.js", "server/main.py")


def test_verify_installed_resources_with_no_declared_resources_reports_nothing(tmp_path: Path) -> None:
    assert verify_installed_resources(tmp_path, ()) == ()


def test_install_one_project_refuses_to_install_a_build_missing_a_declared_required_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # this project's own literal acceptance test: build.sh ran and reported the
    # right version, but silently never produced the UI resource this
    # profile curated as required - must be caught here, before the image
    # is ever promoted, not discovered later on real hardware.
    fake_run, _calls, target = _fake_run_for_install(tmp_path, pre_build_version="0.4.8", post_build_version="0.4.8")
    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    with pytest.raises(ImageBuildError, match="missing 1 required resource"):
        _install_one_project(
            _entry(commit_sha="c" * 40, version="0.4.8", required_resources=("dist/index.html",)), tmp_path
        )
    assert not (target / "dist" / "index.html").exists(), "the fixture itself never created this - proves the check is real, not vacuous"


def test_install_one_project_succeeds_when_every_declared_required_resource_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run, _calls, target = _fake_run_for_install(tmp_path, pre_build_version="0.4.8", post_build_version="0.4.8")

    def fake_run_with_dist(*command, **kwargs):
        result = fake_run(*command, **kwargs)
        if command[0] == "chroot":
            (target / "dist").mkdir(parents=True, exist_ok=True)
            (target / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
        return result

    monkeypatch.setattr(image_builder_module, "_run", fake_run_with_dist)

    real_version = _install_one_project(
        _entry(commit_sha="c" * 40, version="0.4.8", required_resources=("dist/index.html",)), tmp_path
    )
    assert real_version == "0.4.8"


def test_read_real_installed_version_returns_the_real_manifest_value(tmp_path: Path) -> None:
    (tmp_path / "hydra-umc.project.json").write_text(json.dumps({"version": "1.2.3"}), encoding="utf-8")
    assert _read_real_installed_version(tmp_path, "some-project") == "1.2.3"


def test_read_real_installed_version_falls_back_honestly_when_the_manifest_is_unreadable(tmp_path: Path) -> None:
    # No manifest written at all - a real post-build failure mode this
    # function must never silently paper over with a fabricated version.
    result = _read_real_installed_version(tmp_path, "some-project")
    assert "unknown" in result
    assert "some-project" in result


def test_fetch_base_image_refuses_to_start_a_download_with_no_real_room_for_it(
    fixture_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_usage = shutil.disk_usage(tmp_path)._replace(free=1024)  # 1 KB free, real type
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: fake_usage)
    source = BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256="")
    with pytest.raises(ImageBuildError, match="not enough free disk space"):
        fetch_base_image(source, tmp_path)
    # Must fail BEFORE ever downloading anything, not partway through.
    assert not (tmp_path / "image.img").exists()
    assert not (tmp_path / "image.img.part").exists()


# scan_for_leaked_secrets real tests. No real loop-mount needed -
# the function only ever reads from a plain directory tree, so a real
# tmp_path standing in for a mounted rootfs exercises the real logic
# end-to-end without any Linux-only privilege.


def test_scan_for_leaked_secrets_is_clean_on_a_fresh_rootfs_with_nothing_provisioned(tmp_path: Path) -> None:
    (tmp_path / "etc").mkdir()
    (tmp_path / "root").mkdir()
    assert scan_for_leaked_secrets(tmp_path) == []


def test_scan_for_leaked_secrets_finds_a_real_wpa_supplicant_psk(tmp_path: Path) -> None:
    wpa_dir = tmp_path / "etc" / "wpa_supplicant"
    wpa_dir.mkdir(parents=True)
    (wpa_dir / "wpa_supplicant.conf").write_text(
        'network={\n    ssid="HomeWifi"\n    psk="a real password, never this"\n}\n', encoding="utf-8"
    )
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert "wpa_supplicant.conf" in findings[0]


def test_scan_for_leaked_secrets_finds_a_real_networkmanager_psk(tmp_path: Path) -> None:
    nm_dir = tmp_path / "etc" / "NetworkManager" / "system-connections"
    nm_dir.mkdir(parents=True)
    (nm_dir / "HomeWifi.nmconnection").write_text(
        "[wifi-security]\nkey-mgmt=wpa-psk\npsk=a-real-password\n", encoding="utf-8"
    )
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert "HomeWifi.nmconnection" in findings[0]


def test_scan_for_leaked_secrets_finds_a_real_private_ssh_key_but_not_the_public_half(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "root" / ".ssh"
    ssh_dir.mkdir(parents=True)
    (ssh_dir / "id_ed25519").write_bytes(b"-----BEGIN OPENSSH PRIVATE KEY-----\nreal key material\n")
    (ssh_dir / "id_ed25519.pub").write_bytes(b"ssh-ed25519 AAAAC3Nz... user@host\n")
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert "id_ed25519" in findings[0] and "id_ed25519.pub" not in findings[0]


def test_scan_for_leaked_secrets_finds_a_real_populated_home_users_ssh_key_too(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "home" / "pi" / ".ssh"
    ssh_dir.mkdir(parents=True)
    (ssh_dir / "id_rsa").write_bytes(b"-----BEGIN RSA PRIVATE KEY-----\nreal key material\n")
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert str(Path("home") / "pi" / ".ssh" / "id_rsa") in findings[0]


def test_scan_for_leaked_secrets_finds_a_real_nonempty_shell_history(tmp_path: Path) -> None:
    root_home = tmp_path / "root"
    root_home.mkdir()
    (root_home / ".bash_history").write_text("curl -u admin:real-password https://example.test\n", encoding="utf-8")
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert ".bash_history" in findings[0]


def test_scan_for_leaked_secrets_ignores_a_real_but_empty_shell_history(tmp_path: Path) -> None:
    root_home = tmp_path / "root"
    root_home.mkdir()
    (root_home / ".bash_history").write_text("", encoding="utf-8")
    assert scan_for_leaked_secrets(tmp_path) == []


def test_scan_for_leaked_secrets_finds_a_real_env_file_anywhere_under_a_home_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "home" / "pi" / "some-project"
    project_dir.mkdir(parents=True)
    (project_dir / ".env").write_text("API_KEY=a-real-secret-value\n", encoding="utf-8")
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 1
    assert ".env" in findings[0]


def test_scan_for_leaked_secrets_reports_every_real_finding_not_just_the_first(tmp_path: Path) -> None:
    root_home = tmp_path / "root"
    root_home.mkdir()
    (root_home / ".bash_history").write_text("a real command\n", encoding="utf-8")
    ssh_dir = root_home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_bytes(b"-----BEGIN OPENSSH PRIVATE KEY-----\nreal key material\n")
    findings = scan_for_leaked_secrets(tmp_path)
    assert len(findings) == 2


# real output-side inventory hashing -
# _hash_directory_tree() itself, pure and fully testable without a real
# mount/chroot pipeline.
def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_hash_directory_tree_is_stable_for_the_same_real_content(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", "hello")
    _write(tmp_path / "sub" / "b.txt", "world")
    assert _hash_directory_tree(tmp_path) == _hash_directory_tree(tmp_path)


def test_hash_directory_tree_changes_when_a_files_real_content_changes(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", "hello")
    before = _hash_directory_tree(tmp_path)
    _write(tmp_path / "a.txt", "hello, but tampered with")
    after = _hash_directory_tree(tmp_path)
    assert before != after


def test_hash_directory_tree_changes_when_a_file_is_added(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", "hello")
    before = _hash_directory_tree(tmp_path)
    _write(tmp_path / "b.txt", "a new real file")
    after = _hash_directory_tree(tmp_path)
    assert before != after


def test_hash_directory_tree_changes_when_a_file_moves_to_a_different_real_path(tmp_path: Path) -> None:
    # Same real content, different real relative path - a real tamper that
    # a naive "hash of all file contents, order-independent" scheme would
    # miss entirely.
    tree_a = tmp_path / "a"
    _write(tree_a / "here" / "x.txt", "same content")
    tree_b = tmp_path / "b"
    _write(tree_b / "elsewhere" / "x.txt", "same content")
    assert _hash_directory_tree(tree_a) != _hash_directory_tree(tree_b)


def test_hash_directory_tree_is_independent_of_real_filesystem_walk_order(tmp_path: Path) -> None:
    tree_a = tmp_path / "a"
    _write(tree_a / "zzz.txt", "1")
    _write(tree_a / "aaa.txt", "2")
    _write(tree_a / "mmm" / "nested.txt", "3")
    tree_b = tmp_path / "b"
    _write(tree_b / "aaa.txt", "2")
    _write(tree_b / "mmm" / "nested.txt", "3")
    _write(tree_b / "zzz.txt", "1")
    assert _hash_directory_tree(tree_a) == _hash_directory_tree(tree_b)


def test_hash_directory_tree_of_an_empty_directory_is_a_real_stable_value(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _hash_directory_tree(empty) == hashlib.sha256(b"").hexdigest()


def test_hash_directory_tree_hashes_a_symlink_by_its_own_real_target_never_following_it(tmp_path: Path) -> None:
    outside_secret = tmp_path.parent / "outside-the-tree-secret.txt"
    outside_secret.write_text("must never be pulled into the hash", encoding="utf-8")
    tree = tmp_path / "tree"
    tree.mkdir()
    link = tree / "link.txt"
    link.symlink_to(outside_secret)
    # Must not raise, and must not depend on outside_secret's own content -
    # changing that content must never change this tree's own hash.
    first = _hash_directory_tree(tree)
    outside_secret.write_text("changed - must still not matter", encoding="utf-8")
    second = _hash_directory_tree(tree)
    assert first == second


def test_hash_directory_tree_never_raises_on_a_real_dangling_symlink(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "broken.txt").symlink_to(tmp_path / "does-not-exist.txt")
    # Must complete, not raise FileNotFoundError trying to read through it.
    _hash_directory_tree(tree)


# ---------------------------------------------------------------------------
# a real, dedicated end-to-end test of build_image stopping
# partway through - a per-project install failure raised from inside the
# real install loop (the same real code path a real mid-build cancellation
# or crash exercises: the `finally` block's own real cleanup, and never
# promoting the raw image). check_build_platform() and every real
# subprocess call (_run, and the finally block's own direct subprocess.run
# calls) are monkeypatched - this asserts this project's OWN pipeline logic
# for real, not a real loop-mount/chroot, which needs actual Linux root
# this dev environment does not have (see this module's own HONEST
# PLATFORM BOUNDARY comment).
# ---------------------------------------------------------------------------


def _fake_subprocess_run(calls: list[list[str]]):
    class _FakeCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake(command, **kwargs):
        calls.append(list(command))
        return _FakeCompleted()

    return fake


def _install_pipeline_fake_run(succeeding_target: Path):
    """Real git clone/chroot/checkout sequence for ONE succeeding
    project, plus the losetup/mount calls `build_image()` itself makes -
    everything BEFORE `_install_one_project()` ever gets called for a
    second, deliberately-broken entry (which raises before making any
    `_run` call of its own - see `_entry(commit_sha=None)`)."""
    calls: list[list[str]] = []

    def fake_run(*command: str, **kwargs):
        calls.append(list(command))
        if command[:2] == ("losetup", "--find"):
            class _Completed:
                stdout = "/dev/loop0\n"

            return _Completed()
        if command[0] == "mount":
            return None
        if command[:2] == ("git", "clone"):
            succeeding_target.mkdir(parents=True)
            (succeeding_target / "build.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (succeeding_target / "hydra-umc.project.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
            return None
        if command[0] == "chroot":
            return None
        if command[:4] == ("git", "-C", str(succeeding_target), "checkout") and command[-2:] == ("--", "."):
            return None
        return None

    return fake_run, calls


def test_build_image_stopping_mid_install_still_cleans_up_and_never_promotes(
    fixture_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))

    succeeding_target = tmp_path / "work" / "mnt" / "rootfs" / "opt" / "hydra-umc" / "hydra-umc-server"
    fake_run, run_calls = _install_pipeline_fake_run(succeeding_target)
    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    subprocess_calls: list[list[str]] = []
    monkeypatch.setattr(image_builder_module.subprocess, "run", _fake_subprocess_run(subprocess_calls))

    plan = EcosystemPlan(
        entries=(
            _entry(name="HYDRA-UMC-SERVER", version="1.0.0", commit_sha="c" * 40),
            # No real, resolved commit SHA - _install_one_project refuses
            # immediately, before this entry ever makes an _run call of
            # its own. Models a real mid-build stop exactly as honestly
            # as an external cancellation would: the loop already
            # installed one real project, then stopped.
            _entry(name="HYDRA-UMC-BROKEN", commit_sha=None),
        ),
        discovery_errors=(),
    )
    output_path = tmp_path / "out" / "hydra-umc-cm5.img"
    progress_phases: list[str] = []

    result = build_image(
        source=BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256=""),
        plan=plan,
        firstboot=None,
        work_dir=tmp_path / "work",
        output_path=output_path,
        progress=lambda update: progress_phases.append(update.phase),
    )

    assert result.ok is False
    assert "HYDRA-UMC-BROKEN" in result.error
    assert "no real, resolved commit SHA" in result.error
    # The one project that genuinely finished before the stop is still
    # honestly reported.
    assert len(result.installed) == 1
    assert result.installed[0].startswith("HYDRA-UMC-SERVER@1.0.0#sha256:")
    # Never promoted - a real caller must never see a half-built image at
    # the real output path.
    assert not output_path.exists()
    # The real cleanup (umount boot, umount rootfs, losetup -d) ran
    # unconditionally, via the direct subprocess.run path (never the
    # check=True _run wrapper, which would abort on a real failure here).
    cleanup_labels = [call[0] for call in subprocess_calls]
    assert cleanup_labels == ["umount", "umount", "losetup"]
    assert subprocess_calls[2] == ["losetup", "-d", "/dev/loop0"]
    # secret-scan/firstboot-config never ran for a build that stopped
    # mid-install - "secret-scan" would appear in progress_phases if they had.
    assert "secret-scan" not in progress_phases
    assert "unmount" in progress_phases, "unmount is still reported even though the build failed"


def test_build_image_stopping_on_a_real_subprocess_failure_also_cleans_up_and_never_promotes(
    fixture_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A real, unrelated subprocess failure (git over a flaky connection,
    # say) - _run()'s own check=True raises subprocess.CalledProcessError,
    # never ImageBuildError. Same real stop-cleanup-report contract must
    # still hold.
    import subprocess

    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))

    subprocess_calls: list[list[str]] = []
    monkeypatch.setattr(image_builder_module.subprocess, "run", _fake_subprocess_run(subprocess_calls))

    def fake_run(*command: str, **kwargs):
        if command[:2] == ("losetup", "--find"):
            class _Completed:
                stdout = "/dev/loop0\n"

            return _Completed()
        if command[0] == "mount":
            return None
        if command[:2] == ("git", "clone"):
            raise subprocess.CalledProcessError(returncode=128, cmd=list(command), stderr="fatal: unable to access: network unreachable")
        return None

    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    plan = EcosystemPlan(entries=(_entry(name="HYDRA-UMC-SERVER", commit_sha="c" * 40),), discovery_errors=())
    output_path = tmp_path / "out.img"

    result = build_image(
        source=BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256=""),
        plan=plan, firstboot=None, work_dir=tmp_path / "work", output_path=output_path, progress=None,
    )

    assert result.ok is False
    assert "HYDRA-UMC-SERVER" in result.error
    assert "returned non-zero exit status 128" in result.error
    assert not output_path.exists()
    assert [call[0] for call in subprocess_calls] == ["umount", "umount", "losetup"]


def test_build_image_reports_platform_check_failure_without_touching_any_real_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(False, "not a real Linux host"))
    calls: list[list[str]] = []
    monkeypatch.setattr(image_builder_module, "_run", lambda *a, **k: calls.append(list(a)) or None)

    result = build_image(
        source=BaseImageSource(label="fixture", url="http://127.0.0.1:1/image.img", sha256=""),
        plan=EcosystemPlan(entries=(), discovery_errors=()),
        firstboot=None,
        work_dir=tmp_path / "work",
        output_path=tmp_path / "out.img",
        progress=None,
    )

    assert result.ok is False
    assert result.error == "not a real Linux host"
    assert calls == [], "a platform-check failure must never attempt a real subprocess call"


# ---------------------------------------------------------------------------
# Real per-submodule timeout: a hung/misbehaving project's own clone/
# checkout/chrooted build.sh must never be able to hang an entire image
# build forever - caught here as a clear, named subprocess.TimeoutExpired,
# not left as an unbounded wait.
# ---------------------------------------------------------------------------


def test_install_one_project_threads_the_real_timeout_into_every_run_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run, _calls, _target = _fake_run_for_install(tmp_path, pre_build_version="0.4.8", post_build_version="0.4.8")

    # calls only records positional command args, not kwargs - a
    # kwarg-capturing wrapper around the same fake_run asserts the real
    # timeout value reaches every single _run() call this function makes
    # (clone, checkout, chroot build.sh, and the post-build restore
    # checkout).
    seen_timeouts: list[float | None] = []

    def capturing_fake_run(*command: str, **kwargs):
        seen_timeouts.append(kwargs.get("timeout"))
        return fake_run(*command, **kwargs)

    monkeypatch.setattr(image_builder_module, "_run", capturing_fake_run)
    _install_one_project(_entry(commit_sha="c" * 40, version="0.4.8"), tmp_path, timeout_seconds=42.0)

    assert seen_timeouts, "at least one _run() call must have happened"
    assert all(t == 42.0 for t in seen_timeouts), f"every _run() call must get the real configured timeout, got {seen_timeouts}"


def test_build_image_stopping_on_a_real_per_submodule_timeout_also_cleans_up_and_never_promotes(
    fixture_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))

    subprocess_calls: list[list[str]] = []
    monkeypatch.setattr(image_builder_module.subprocess, "run", _fake_subprocess_run(subprocess_calls))

    def fake_run(*command: str, **kwargs):
        if command[:2] == ("losetup", "--find"):
            class _Completed:
                stdout = "/dev/loop0\n"

            return _Completed()
        if command[0] == "mount":
            return None
        if command[:2] == ("git", "clone"):
            # Models a real hung clone (a stalled network, an interactive
            # credential prompt this pipeline should never hit) - the real
            # subprocess.run(..., timeout=...) contract raises exactly
            # this, never hangs the calling thread forever.
            raise subprocess.TimeoutExpired(cmd=list(command), timeout=42.0)
        return None

    monkeypatch.setattr(image_builder_module, "_run", fake_run)

    plan = EcosystemPlan(entries=(_entry(name="HYDRA-UMC-SERVER", commit_sha="c" * 40),), discovery_errors=())
    output_path = tmp_path / "out.img"

    result = build_image(
        source=BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256=""),
        plan=plan,
        firstboot=None,
        work_dir=tmp_path / "work",
        output_path=output_path,
        progress=None,
        project_timeout_seconds=42.0,
    )

    assert result.ok is False
    assert "HYDRA-UMC-SERVER" in result.error
    assert "timed out after 42" in result.error
    assert not output_path.exists()
    # The real cleanup still ran, exactly as it does for any other real
    # per-project failure (ImageBuildError, CalledProcessError).
    assert [call[0] for call in subprocess_calls] == ["umount", "umount", "losetup"]


def test_build_image_defaults_to_the_real_documented_project_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # DEFAULT_PROJECT_TIMEOUT_SECONDS is the real value build_image() uses
    # when a caller (main.py's own CLI, qt_gui.py's own local build path)
    # does not explicitly override it - asserted directly against
    # build_image's own signature default so the two can never silently
    # drift apart.
    import inspect

    default = inspect.signature(build_image).parameters["project_timeout_seconds"].default
    assert default == DEFAULT_PROJECT_TIMEOUT_SECONDS
    assert default and default > 0, "the real default must be a positive, finite timeout, not unlimited"


def test_hash_directory_tree_ignores_git_metadata_and_bytecode_caches(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "print(1)")
    before = _hash_directory_tree(tmp_path)
    _write(tmp_path / ".git" / "index", "clone-time noise")
    _write(tmp_path / "pkg" / "__pycache__" / "m.cpython-311.pyc", "mtime-dependent")
    _write(tmp_path / "pkg" / "stray.pyc", "mtime-dependent")
    _write(tmp_path / ".pytest_cache" / "v" / "x", "cache")
    assert _hash_directory_tree(tmp_path) == before


def test_hash_directory_tree_still_sees_real_source_next_to_ignored_paths(tmp_path: Path) -> None:
    _write(tmp_path / "pkg" / "__pycache__" / "m.pyc", "noise")
    before = _hash_directory_tree(tmp_path)
    _write(tmp_path / "pkg" / "m.py", "real source")
    assert _hash_directory_tree(tmp_path) != before

