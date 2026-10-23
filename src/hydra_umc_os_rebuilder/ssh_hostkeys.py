# =============================================================================
# HYDRA-UMC-OS-REBUILDER - src/hydra_umc_os_rebuilder/ssh_hostkeys.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Trust on first use for the SSH host key of a remote build machine, with a pinned fingerprint.

The first time a host is reached its key is NOT accepted silently: the connection is refused and the message shows the key's
SHA-256 fingerprint. The operator checks it on the machine itself and enters it as the expected fingerprint; only a key whose
fingerprint is equal to that is pinned (stored). From then on the pinned fingerprint is the only one accepted for that host and
port: a different key is refused as a changed key, whatever the operator types.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

KNOWN_HOSTS_ENV = "HYDRA_UMC_OS_REBUILDER_KNOWN_HOSTS"


class HostKeyError(Exception):
    """The host key was not accepted (unknown and unconfirmed, or changed)."""


def default_store_path() -> Path:
    configured = os.environ.get(KNOWN_HOSTS_ENV, "").strip()
    if configured:
        return Path(configured)
    return Path.home() / ".hydra-umc" / "os-rebuilder-known-hosts.json"


def fingerprint_sha256(key_blob: bytes) -> str:
    """OpenSSH style fingerprint: ``SHA256:`` and the unpadded base64 of the SHA-256 of the public key blob."""
    digest = hashlib.sha256(key_blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def normalize_fingerprint(text: str) -> str:
    """Accepts ``SHA256:abc...`` with or without the prefix and with trailing padding; returns the canonical form (empty when empty)."""
    value = text.strip()
    if not value:
        return ""
    if value.upper().startswith("SHA256:"):
        value = value[len("SHA256:"):]
    return "SHA256:" + value.rstrip("=")


def _host_id(host: str, port: int) -> str:
    return f"{host.strip().lower()}:{int(port)}"


class HostKeyStore:
    """The pinned fingerprints, one per host and port, in a small JSON file (an unreadable file is an empty store: nothing is trusted)."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else default_store_path()

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("fingerprint"), str)}

    def pinned(self, host: str, port: int) -> str | None:
        entry = self._load().get(_host_id(host, port))
        return entry["fingerprint"] if entry else None

    def pin(self, host: str, port: int, key_type: str, fingerprint: str) -> None:
        data = self._load()
        data[_host_id(host, port)] = {"type": key_type, "fingerprint": fingerprint}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)


def decide(store: HostKeyStore, host: str, port: int, key_type: str, key_blob: bytes, expected: str = "") -> str:
    """Judges one presented host key. Returns the fingerprint when accepted (pinning it on first use); raises HostKeyError otherwise."""
    fingerprint = fingerprint_sha256(key_blob)
    pinned = store.pinned(host, port)
    if pinned is not None:
        if hmac.compare_digest(pinned.encode("utf-8"), fingerprint.encode("utf-8")):
            return fingerprint
        raise HostKeyError(
            f"the host key of {host}:{port} CHANGED: it is now {fingerprint} but {pinned} was pinned. "
            "Someone may be impersonating the machine; if it was reinstalled on purpose, remove its entry from "
            f"{store.path} and connect again."
        )
    wanted = normalize_fingerprint(expected)
    if not wanted:
        raise HostKeyError(
            f"first connection to {host}:{port}: its {key_type} key is {fingerprint}. Check that fingerprint on the machine itself, "
            "enter it as the expected host key fingerprint and build again."
        )
    if not hmac.compare_digest(wanted.encode("utf-8"), fingerprint.encode("utf-8")):
        raise HostKeyError(f"the host key of {host}:{port} is {fingerprint}, not the {wanted} that was entered: refusing to connect.")
    store.pin(host, port, key_type, fingerprint)
    return fingerprint


def make_policy(store: HostKeyStore, port: int, expected: str = ""):
    """A paramiko missing-host-key policy that applies `decide`. paramiko is imported here so that the rest of this module needs none."""
    import paramiko

    class PinnedHostKeyPolicy(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self, client, hostname, key):  # noqa: ANN001 - paramiko's signature
            try:
                decide(store, hostname, port, key.get_name(), key.asbytes(), expected)
            except HostKeyError as error:
                raise paramiko.SSHException(str(error)) from error

    return PinnedHostKeyPolicy()
