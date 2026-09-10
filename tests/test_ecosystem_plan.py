# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_ecosystem_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import http.server
import json
import threading

import pytest

from hydra_umc_updater.github_client import RemoteDiscovery, RemoteStatus
from hydra_umc_updater.project_manifest import ProjectManifest
from hydra_umc_updater.registry import ProjectEntry
from hydra_umc_os_rebuilder import ecosystem_plan as ecosystem_plan_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry, build_plan, plan_summary_lines, resolve_commit_shas


def _manifest(name: str, version: str, deployment_target: str, role: str = "service", stack: str = "python") -> ProjectManifest:
    return ProjectManifest(
        schema_version="1.0",
        ecosystem="HYDRA-UMC",
        name=name,
        version=version,
        role=role,
        stack=stack,
        technologies=("Python",),
        deployment_target=deployment_target,
        maturity="functional",
        family="Test Family",
        parent=None,
        native_version_file="pyproject.toml",
        native_version_pattern=r'version = "(\d+)\.(\d+)\.(\d+)"',
        build="test",
        notes="test",
    )


def _entry(name: str) -> ProjectEntry:
    return ProjectEntry(name=name, stack="python", version_file="pyproject.toml", pattern=r'version = "(\d+)\.(\d+)\.(\d+)"')


def _status(name: str, version, manifest: ProjectManifest | None) -> RemoteStatus:
    return RemoteStatus(entry=_entry(name), version=version, manifest=manifest)


class _V:
    """Minimal stand-in matching version_parse.Version's own str()."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __str__(self) -> str:
        return self._text


def test_only_cm5_deployment_targets_survive_the_plan() -> None:
    discovery = RemoteDiscovery(
        projects=(
            _status("HYDRA-UMC-SERVER", _V("0.4.8"), _manifest("HYDRA-UMC-SERVER", "0.4.8", "cm5", role="api", stack="node")),
            _status("HYDRA-UMC-UPDATER", _V("0.2.6"), _manifest("HYDRA-UMC-UPDATER", "0.2.6", "user-pc")),
            _status("HYDRA-UMC-ANDROID-CONTROL", _V("0.2.8"), _manifest("HYDRA-UMC-ANDROID-CONTROL", "0.2.8", "mobile")),
        ),
        errors=(),
    )
    plan = build_plan(discovery)
    assert [entry.name for entry in plan.entries] == ["HYDRA-UMC-SERVER"]
    assert plan.entries[0].version == "0.4.8"
    assert plan.entries[0].git_url == "https://github.com/JuanenRac/HYDRA-UMC-SERVER.git"


def test_entries_with_no_manifest_or_version_are_skipped() -> None:
    discovery = RemoteDiscovery(
        projects=(
            _status("Broken", None, None),
            _status("AlsoBroken", _V("1.0.0"), None),
        ),
        errors=("Broken: manifest lookup failed",),
    )
    plan = build_plan(discovery)
    assert plan.entries == ()
    assert plan.discovery_errors == ("Broken: manifest lookup failed",)


def test_plan_is_sorted_by_name_case_insensitively() -> None:
    discovery = RemoteDiscovery(
        projects=(
            _status("zebra-project", _V("1.0.0"), _manifest("zebra-project", "1.0.0", "cm5")),
            _status("Alpha-Project", _V("1.0.0"), _manifest("Alpha-Project", "1.0.0", "cm5")),
        ),
        errors=(),
    )
    plan = build_plan(discovery)
    assert [entry.name for entry in plan.entries] == ["Alpha-Project", "zebra-project"]


# =============================================================================
# IMAGE-01 (P1):
# resolve_commit_shas() real network pass - a real local fixture HTTP
# server standing in for GitHub's own `/repos/:owner/:repo/commits/:branch`
# endpoint, no network mocking of the request/response machinery itself.
# =============================================================================


class _FakeGitHubCommitsHandler(http.server.BaseHTTPRequestHandler):
    # {"owner/repo/branch": sha, or None to mean "respond 404"}
    shas: dict[str, str | None] = {}

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        # Real path shape: /repos/{owner}/{name}/commits/{branch}
        parts = self.path.strip("/").split("/")
        key = None
        if len(parts) == 5 and parts[0] == "repos" and parts[3] == "commits":
            key = f"{parts[1]}/{parts[2]}/{parts[4]}"
        sha = self.shas.get(key) if key is not None else None
        if sha is None:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"sha": sha}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - silence test output
        pass


@pytest.fixture()
def fake_github_commits(monkeypatch: pytest.MonkeyPatch):
    _FakeGitHubCommitsHandler.shas = {}
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakeGitHubCommitsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(ecosystem_plan_module, "GITHUB_API_BASE", f"http://127.0.0.1:{server.server_port}")
    try:
        yield _FakeGitHubCommitsHandler
    finally:
        server.shutdown()
        thread.join()


def _plan(*entries: EcosystemPlanEntry) -> EcosystemPlan:
    return EcosystemPlan(entries=tuple(entries), discovery_errors=())


def test_resolve_commit_shas_fills_in_the_real_immutable_sha(fake_github_commits) -> None:
    fake_github_commits.shas = {"JuanenRac/HYDRA-UMC-SERVER/main": "a" * 40}
    plan = _plan(
        EcosystemPlanEntry(
            name="HYDRA-UMC-SERVER", version="0.4.8", role="api", stack="node",
            git_url="https://github.com/JuanenRac/HYDRA-UMC-SERVER.git",
        )
    )

    resolved = resolve_commit_shas(plan)

    assert len(resolved.entries) == 1
    assert resolved.entries[0].commit_sha == "a" * 40
    assert resolved.discovery_errors == ()


def test_resolve_commit_shas_excludes_an_entry_it_cannot_resolve_a_real_sha_for(fake_github_commits) -> None:
    # No entry registered in fake_github_commits.shas at all - every
    # lookup 404s, the real "this branch/repo doesn't exist" case.
    plan = _plan(
        EcosystemPlanEntry(
            name="HYDRA-UMC-GHOST", version="0.0.1", role="api", stack="node",
            git_url="https://github.com/JuanenRac/HYDRA-UMC-GHOST.git",
        )
    )

    resolved = resolve_commit_shas(plan)

    assert resolved.entries == ()
    assert len(resolved.discovery_errors) == 1
    assert "HYDRA-UMC-GHOST" in resolved.discovery_errors[0]
    assert "could not resolve a real commit SHA" in resolved.discovery_errors[0]


def test_resolve_commit_shas_never_fabricates_a_sha_for_one_entry_just_because_another_resolved(
    fake_github_commits,
) -> None:
    # IMAGE-01's own real bar: a partial failure must exclude ONLY the
    # entry that actually failed, never silently degrade to an unpinned
    # build for it, and never contaminate the entry that DID resolve.
    fake_github_commits.shas = {"JuanenRac/HYDRA-UMC-SERVER/main": "b" * 40}
    plan = _plan(
        EcosystemPlanEntry(
            name="HYDRA-UMC-SERVER", version="0.4.8", role="api", stack="node",
            git_url="https://github.com/JuanenRac/HYDRA-UMC-SERVER.git",
        ),
        EcosystemPlanEntry(
            name="HYDRA-UMC-GHOST", version="0.0.1", role="api", stack="node",
            git_url="https://github.com/JuanenRac/HYDRA-UMC-GHOST.git",
        ),
    )

    resolved = resolve_commit_shas(plan)

    assert [entry.name for entry in resolved.entries] == ["HYDRA-UMC-SERVER"]
    assert resolved.entries[0].commit_sha == "b" * 40
    assert len(resolved.discovery_errors) == 1
    assert "HYDRA-UMC-GHOST" in resolved.discovery_errors[0]


def test_plan_summary_lines_include_a_total_and_error_count() -> None:
    discovery = RemoteDiscovery(
        projects=(_status("HYDRA-UMC-SERVER", _V("0.4.8"), _manifest("HYDRA-UMC-SERVER", "0.4.8", "cm5", role="api", stack="node")),),
        errors=("SomeRepo: HTTP 404",),
    )
    plan = build_plan(discovery)
    lines = plan_summary_lines(plan)
    assert "HYDRA-UMC-SERVER 0.4.8 (api/node)" in lines
    assert any("1 repositor" in line for line in lines)
