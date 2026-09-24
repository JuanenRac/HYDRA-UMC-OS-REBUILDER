<!-- =============================================================================
HYDRA-UMC-OS-REBUILDER - Maturity exit criteria
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Exit Criteria: Scaffolding to Functional

This project is labelled `scaffolding`. The label moves to `functional` only
when every item below is true and verifiable in the repository (a test, a
CI check or a reproducible command) - not when the code merely exists.

- [ ] A build emits a reproducible image with an SBOM, hashes and board metadata.
- [ ] The image is verified before flashing, and no target is ever overwritten by default.
- [ ] Two builds from the same frozen manifest are compared and the result is recorded.

Verified on real hardware or services is a separate, later step: a passing
software check does not certify physical behaviour.
