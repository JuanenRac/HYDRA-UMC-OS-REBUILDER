# Simulation bench

Runs the image pipeline, the first-boot files, the release and golden-image commands, the profile signing and the boot test against fakes only: no loop device, no QEMU, no board and no network. The build is replaced by a recorder, QEMU by a launcher that prints a serial log, GitHub by a fixed plan, and the Linux host by a twin that keeps its loop devices and mounts and fails on command. The workflow `simulation.yml` runs it, and a second job measures the coverage of the program with a floor that does not go down.

Scenarios:

- the base image is downloaded and checked against its pinned digest (a tampered file, a missing or garbled sidecar and a full disk are refused), and a project is cloned at its pinned commit, built in the chroot with the pseudo file systems mounted, put back to the pinned commit and checked for the required resources (`tests/test_image_builder.py`, `tests/test_pipeline_guards.py`, `tests/test_chroot_and_remote.py`);
- a build that stops in the middle, by a refusal, a failing command or a time-out, still unmounts everything, detaches the loop device and never promotes the image;
- a leaked secret, a key or a shell history in the root file system stops the promotion (`scan_for_leaked_secrets`);
- the first-boot configuration, the installer tree check, the golden image and its delta, the signed profile, the signed corpus and the boot extraction are exercised over fixtures (`tests/test_golden_image.py`, `tests/test_installer_check_and_boot_extract.py`, `tests/test_cli_commands.py`, `tests/test_language_hostkeys_boot_edges.py`);
- every single step of the build (the download, the loop device, each mount of the partitions and of the chroot, each clone, checkout and chrooted build, the platform command, each unmount, the release of the loop device) fails in turn, once with an exit status and once with a time-out (`tests/test_simulation_faults.py`): the build always returns a result and names the failure, no half-built image reaches the output path, no mount, loop device or half-downloaded file is left (except what the failing release itself was to free, and then the result says so), and a failure in the second project names that project and keeps the first one in the list of what was installed;
- ten failures drawn from a fixed seed, each followed by a build from a fresh base image over the same folders, give the same content hashes as a build that never failed.

The evidence of this project is `simulator`: it says nothing about a real kernel, a real `chroot`, a real SD card or eMMC, or a real board.

Physical tests still pending:

- a Linux host with root, a real Raspberry Pi OS image and the real ecosystem: build an image, start it on a CM5, and unplug the build host's power in the middle of the install phase on a second attempt; expected: the first image boots and every installed project reports the version of its manifest, and after the cut the loop device and mounts of the host are released by a reboot, and a new build from the same folders finishes with the same content hashes;
- a `jetson` or `rk3588` profile: build and boot the image on the module; expected: the platform packages and units are present and active (planned only; no such image was built).
