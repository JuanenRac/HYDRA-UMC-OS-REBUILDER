# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Artifact cache by (project, commit): artifact_cache.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A project at a given commit always builds to the same files, so what an install produced is kept on the host under
# <directory>/<project>/<commit>/ and reused by the next image instead of being built again. Each entry holds the
# `payload` folder and an `entry.json` with the SHA-256 of the payload tree; a lookup checks the hash and drops an entry
# that no longer matches. The cache keeps to `max_gb` by removing the entries used least recently. Off by default
# (`artifact_cache.enabled` of the configuration file); the commit must be a full 40-character SHA, so a moving branch
# name can never be cached.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

_HEX = set("0123456789abcdef")
_NAME = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


class CacheError(ValueError):
    """An entry or a cache that cannot be used."""


def tree_hash(root: Path) -> str:
    """SHA-256 over the relative paths and the bytes of every file below `root`, in a fixed order."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _size(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())


class ArtifactCache:
    def __init__(self, directory: Path, max_gb: float = 4.0, *, enabled: bool = True) -> None:
        self.directory = directory
        self.max_bytes = int(max_gb * (1 << 30))
        self.enabled = enabled

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ArtifactCache | None":
        """None unless the cache is switched on and has a folder."""
        options = config["artifact_cache"]
        if not options["enabled"] or not options["directory"]:
            return None
        return cls(Path(str(options["directory"])), float(options["max_gb"]))

    def _entry(self, project: str, commit: str) -> Path:
        if not project or project.startswith(".") or any(ch not in _NAME for ch in project):
            raise CacheError(f"not a project name: {project!r}")
        if len(commit) != 40 or any(ch not in _HEX for ch in commit):
            raise CacheError(f"the cache keys on a full 40-character commit, not {commit!r}")
        return self.directory / project / commit

    def lookup(self, project: str, commit: str) -> Path | None:
        """The cached payload, or None (also when the stored hash no longer matches: that entry is removed)."""
        entry = self._entry(project, commit)
        meta_file = entry / "entry.json"
        if not self.enabled or not meta_file.is_file():
            return None
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        if meta.get("tree_sha256") != tree_hash(entry / "payload"):
            shutil.rmtree(entry, ignore_errors=True)
            return None
        meta["last_used"] = time.time()
        meta_file.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return entry / "payload"

    def store(self, project: str, commit: str, source: Path) -> Path:
        """Copy `source` in as the payload of (project, commit), then bring the cache back under its limit."""
        if not self.enabled:
            raise CacheError("the artifact cache is switched off")
        entry = self._entry(project, commit)
        if not source.is_dir():
            raise CacheError(f"{source} is not a folder")
        shutil.rmtree(entry, ignore_errors=True)
        payload = entry / "payload"
        shutil.copytree(source, payload, symlinks=True)
        meta = {"project": project, "commit": commit, "tree_sha256": tree_hash(payload), "bytes": _size(payload), "last_used": time.time()}
        (entry / "entry.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.prune(keep=(project, commit))
        return payload

    def entries(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for meta_file in sorted(self.directory.glob("*/*/entry.json")) if self.directory.is_dir() else []:
            try:
                found.append(json.loads(meta_file.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return found

    def prune(self, *, keep: tuple[str, str] | None = None) -> list[tuple[str, str]]:
        """Remove the entries used least recently until the cache fits `max_gb`; the entry `keep` is never removed."""
        entries = self.entries()
        total = sum(int(e.get("bytes", 0)) for e in entries)
        removed: list[tuple[str, str]] = []
        for meta in sorted(entries, key=lambda e: float(e.get("last_used", 0))):
            if total <= self.max_bytes:
                break
            key = (str(meta["project"]), str(meta["commit"]))
            if key == keep:
                continue
            shutil.rmtree(self._entry(*key), ignore_errors=True)
            total -= int(meta.get("bytes", 0))
            removed.append(key)
        return removed

    def status(self) -> dict[str, Any]:
        entries = self.entries()
        return {"enabled": self.enabled, "directory": str(self.directory), "entries": len(entries),
                "bytes": sum(int(e.get("bytes", 0)) for e in entries), "max_bytes": self.max_bytes}
