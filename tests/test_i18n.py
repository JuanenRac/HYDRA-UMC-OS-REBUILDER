# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_i18n.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from hydra_umc_os_rebuilder.i18n import LANGUAGES, TRANSLATIONS, text


def test_every_language_carries_every_english_key() -> None:
    english_keys = set(TRANSLATIONS["en"])
    for code, _label in LANGUAGES:
        missing = english_keys - set(TRANSLATIONS[code])
        assert not missing, f"{code} is missing keys: {sorted(missing)}"


def test_text_falls_back_to_english_for_an_unknown_language() -> None:
    assert text("xx", "btn_refresh") == TRANSLATIONS["en"]["btn_refresh"]


def test_text_formats_placeholders() -> None:
    assert text("en", "lbl_projects_found", count=7) == "7 CM5 project(s) found"


def test_text_returns_the_key_itself_for_a_genuinely_unknown_key() -> None:
    assert text("en", "this_key_does_not_exist") == "this_key_does_not_exist"
