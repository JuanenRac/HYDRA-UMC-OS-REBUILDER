@echo off
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : HYDRA-UMC-OS-REBUILDER
REM Script    : run.bat
REM Purpose   : Runtime workflow for the project entry point.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0 - see LICENSE
REM *****************************************************************************
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
REM Keep the normal .bat entry point convenient while handing the graphical
REM default straight to the silent launcher before any banner is printed.
if "%~1"=="" (
    wscript.exe //B "%~dp0run-gui.vbs"
    exit /b %errorlevel%
)
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
echo.
echo *****************************************************************************
echo * HYDRA-UMC-OS-REBUILDER - run.bat
echo * Mode      : RUN WORKFLOW
echo * Author    : JuanenRac (Electro Hobby 3D)
echo * Email     : electrohobby3d@gmail.com
echo * Copyright : (C) 2026 JuanenRac
echo * License   : GPL-3.0 - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Resolve the runtime prerequisites declared by this script.
echo * 2. Start the project entry point and forward user arguments unchanged.
echo * 3. Preserve its result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
REM Runs HYDRA-UMC-OS-REBUILDER. Run build.bat first.
REM
REM Usage:
REM   run.bat                             - launch the windowed GUI (default)
REM   run.bat --cli status                - every ecosystem project's latest real GitHub version
REM   run.bat --cli config --out DIR      - write first-boot config (Wi-Fi/user/hostname/SSH) into DIR
REM   run.bat --cli build-image --out F   - build a ready-to-flash .img (Linux/root only - see docs/CLI_REFERENCE.md)
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m hydra_umc_os_rebuilder.main %*
) else (
    python -m hydra_umc_os_rebuilder.main %*
)

pause
