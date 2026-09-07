#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : HYDRA-UMC-OS-REBUILDER
# Script    : run.sh
# Purpose   : Runtime workflow for the project entry point.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0 - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* HYDRA-UMC-OS-REBUILDER - run.sh"
printf '%s\n' "* Mode      : RUN WORKFLOW"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0 - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Resolve the runtime prerequisites declared by this script."
printf '%s\n' "* 2. Start the project entry point and forward user arguments unchanged."
printf '%s\n' "* 3. Preserve its result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Runs HYDRA-UMC-OS-REBUILDER. Run ./build.sh first.
#
# Usage:
#   ./run.sh                                - launch the windowed GUI (default)
#   ./run.sh --cli status                   - every ecosystem project's latest real GitHub version
#   ./run.sh --cli config --out DIR         - write first-boot config (Wi-Fi/user/hostname/SSH) into DIR
#   ./run.sh --cli build-image --out FILE   - build a ready-to-flash .img (Linux/root only - see docs/CLI_REFERENCE.md)
# --cli never needs a display - safe over SSH on a headless machine.
# See main.py's own header comment.
set -uo pipefail  # no -e: we need to reach the trap below even if the process exits non-zero
cd "$(dirname "$0")"

# Keep the window open if this was double-clicked instead of run from an
# already-open terminal - matters most for `--cli status` (real output a
# double-click would otherwise flash-close before it's readable); the
# default GUI mode already blocks on its own mainloop, so this only adds
# one harmless extra prompt there. Only prompts when stdin is actually a
# terminal (never in CI/piped/non-interactive runs).
trap '[ -t 0 ] && read -r -p "Press Enter to close..." _' EXIT

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
fi

python -m hydra_umc_os_rebuilder.main "$@"
exit $?
