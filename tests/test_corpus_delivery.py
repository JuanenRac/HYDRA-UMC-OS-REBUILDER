# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_corpus_delivery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A signed documentation corpus in the image: valid, altered, unsigned, foreign key, wrong name and not-a-bundle are all decided before the image is touched.

evidence=simulator: the signatures are made with throw-away keys; no release key is involved and no image is mounted. Skipped where the `cryptography`
package is not installed."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from hydra_umc_os_rebuilder import corpus_delivery as cd  # noqa: E402
from hydra_umc_os_rebuilder import main as main_module  # noqa: E402
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan  # noqa: E402
from hydra_umc_os_rebuilder.image_builder import BaseImageSource, build_image  # noqa: E402


def _keypair() -> tuple[ed25519.Ed25519PrivateKey, str]:
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return private, public


def _bundle(directory: Path, release: str = "0.3.0", body: dict | None = None) -> Path:
    path = directory / f"corpus-{release}.json"
    path.write_text(json.dumps(body or {"format": cd.BUNDLE_FORMAT, "release": release, "documents": []}, sort_keys=True), encoding="utf-8")
    return path


def _sign(bundle: Path, private: ed25519.Ed25519PrivateKey) -> None:
    data = bundle.read_bytes()
    bundle.with_name(bundle.name + ".sha256").write_text(f"{hashlib.sha256(data).hexdigest()}  {bundle.name}\n", encoding="ascii")
    bundle.with_name(bundle.name + ".sig").write_text(base64.b64encode(private.sign(data)).decode("ascii") + "\n", encoding="ascii")


@pytest.fixture()
def signed(tmp_path: Path) -> tuple[Path, str, ed25519.Ed25519PrivateKey]:
    private, public = _keypair()
    directory = tmp_path / "release"
    directory.mkdir()
    bundle = _bundle(directory)
    _sign(bundle, private)
    return bundle, public, private


def test_a_corpus_signed_by_the_trusted_key_is_verified(signed) -> None:
    bundle, public, _ = signed
    verified = cd.verify_signed_corpus(bundle, public)
    assert verified.release == "0.3.0" and verified.sha256 == hashlib.sha256(bundle.read_bytes()).hexdigest()
    key_file = bundle.parent / "pub.txt"
    key_file.write_text(public + "\n", encoding="utf-8")
    assert cd.verify_signed_corpus(bundle, str(key_file)).public_key_hex == public


def test_an_altered_corpus_is_refused_even_if_its_digest_file_is_rewritten(signed) -> None:
    bundle, public, _ = signed
    bundle.write_text(bundle.read_text(encoding="utf-8").replace("0.3.0", "0.3.1"), encoding="utf-8")
    with pytest.raises(cd.CorpusDeliveryError, match="changed after it was signed"):
        cd.verify_signed_corpus(bundle, public)
    bundle.with_name(bundle.name + ".sha256").write_text(f"{hashlib.sha256(bundle.read_bytes()).hexdigest()}  x\n", encoding="ascii")
    with pytest.raises(cd.CorpusDeliveryError, match="does not verify"):
        cd.verify_signed_corpus(bundle, public)


@pytest.mark.parametrize("missing", [".sig", ".sha256"])
def test_a_corpus_without_its_signature_or_digest_is_refused(signed, missing: str) -> None:
    bundle, public, _ = signed
    bundle.with_name(bundle.name + missing).unlink()
    with pytest.raises(cd.CorpusDeliveryError, match="missing or unreadable"):
        cd.verify_signed_corpus(bundle, public)


def test_a_corpus_signed_by_another_key_is_refused(signed) -> None:
    bundle, _public, _ = signed
    _other_private, other_public = _keypair()
    with pytest.raises(cd.CorpusDeliveryError, match="does not verify against the trusted key"):
        cd.verify_signed_corpus(bundle, other_public)


def test_a_malformed_signature_or_key_is_refused(signed) -> None:
    bundle, public, _ = signed
    sig = bundle.with_name(bundle.name + ".sig")
    sig.write_text("%%% not base64", encoding="ascii")
    with pytest.raises(cd.CorpusDeliveryError, match="not base64"):
        cd.verify_signed_corpus(bundle, public)
    sig.write_text(base64.b64encode(b"short").decode(), encoding="ascii")
    with pytest.raises(cd.CorpusDeliveryError, match="Ed25519 signature"):
        cd.verify_signed_corpus(bundle, public)
    with pytest.raises(cd.CorpusDeliveryError):
        cd.verify_signed_corpus(bundle, "not a key")


def test_a_signed_file_that_is_not_a_corpus_of_that_release_is_refused(tmp_path: Path) -> None:
    private, public = _keypair()
    for body, message in (
        ({"format": "something/1", "release": "0.3.0"}, "not a corpus bundle"),
        ({"format": cd.BUNDLE_FORMAT, "release": "0.9.9"}, "file name says release"),
    ):
        directory = tmp_path / message.split()[0]
        directory.mkdir()
        bundle = _bundle(directory, body=body)
        _sign(bundle, private)
        with pytest.raises(cd.CorpusDeliveryError, match=message):
            cd.verify_signed_corpus(bundle, public)
    odd = tmp_path / "other.json"
    odd.write_text("{}", encoding="utf-8")
    with pytest.raises(cd.CorpusDeliveryError, match="not named corpus"):
        cd.verify_signed_corpus(odd, public)


def test_install_copies_the_verified_files_and_writes_the_record(signed, tmp_path: Path) -> None:
    bundle, public, _ = signed
    rootfs = tmp_path / "rootfs"
    target = cd.install_signed_corpus(rootfs, cd.verify_signed_corpus(bundle, public))
    assert target == rootfs / "opt" / "hydra-umc" / "docs-qa" / "corpus"
    assert sorted(p.name for p in target.iterdir()) == [
        "corpus-0.3.0.json", "corpus-0.3.0.json.sha256", "corpus-0.3.0.json.sig", "corpus-record.json", "release-public-key.hex",
    ]
    assert (target / "corpus-0.3.0.json").read_bytes() == bundle.read_bytes()
    assert (target / "release-public-key.hex").read_text(encoding="ascii").strip() == public
    record = json.loads((target / "corpus-record.json").read_text(encoding="utf-8"))
    assert record["format"] == cd.RECORD_FORMAT and record["verified_at_build"] is True and record["release"] == "0.3.0"
    # the copy in the image verifies again with the key that travels beside it
    again = cd.verify_signed_corpus(target / "corpus-0.3.0.json", str(target / "release-public-key.hex"))
    assert again.sha256 == record["sha256"]
    # and the image holds no private key material
    assert not [p for p in target.iterdir() if p.suffix in (".pem", ".key", ".seed")]


def _plan_and_source() -> tuple[EcosystemPlan, BaseImageSource]:
    return EcosystemPlan(entries=(), discovery_errors=()), BaseImageSource(label="x", url="https://example.invalid/x.img.xz", sha256="0" * 64)


def test_build_image_refuses_a_bad_corpus_before_anything_is_downloaded(signed, tmp_path: Path) -> None:
    bundle, public, _ = signed
    plan, source = _plan_and_source()
    common = dict(source=source, plan=plan, firstboot=None, work_dir=tmp_path / "work", output_path=tmp_path / "out.img")
    no_key = build_image(**common, corpus_bundle=bundle, corpus_public_key=None)
    assert not no_key.ok and "public key" in (no_key.error or "")
    _other_private, other_public = _keypair()
    foreign = build_image(**common, corpus_bundle=bundle, corpus_public_key=other_public)
    assert not foreign.ok and "was refused" in (foreign.error or "") and "does not verify" in (foreign.error or "")
    bundle.with_name(bundle.name + ".sig").unlink()
    unsigned = build_image(**common, corpus_bundle=bundle, corpus_public_key=public)
    assert not unsigned.ok and "was refused" in (unsigned.error or "")
    assert not (tmp_path / "work").exists()


def test_the_command_line_knows_the_corpus_options_and_the_environment_key() -> None:
    parser = main_module.build_parser()
    args = parser.parse_args(["build-image", "--out", "x.img", "--corpus-bundle", "corpus-0.3.0.json", "--corpus-public-key", "ab"])
    assert args.corpus_bundle == "corpus-0.3.0.json" and args.corpus_public_key == "ab"
    assert main_module.CORPUS_PUBKEY_ENV == "HYDRA_UMC_OS_REBUILDER_CORPUS_PUBKEY"
