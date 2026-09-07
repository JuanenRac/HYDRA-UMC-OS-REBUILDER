# Security Policy 🔒 (HYDRA-UMC-OS-REBUILDER)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x.x   | ✅ Yes    |

## Reporting a Vulnerability

**CRITICAL: Do not report vulnerabilities through public GitHub issues.**

This tool downloads a base OS image over the network, writes real
first-boot credentials (a password hash, an optional SSH public key, a
real Wi-Fi passphrase) onto a boot partition, and - when building an image
- clones and executes each ecosystem project's own `build.sh` inside a
`chroot`. All three are real, meaningful attack surfaces. If you discover a
vulnerability affecting:

- **Base image integrity** - a way to make `build-image` accept a base
  image whose checksum does not actually match what was downloaded.
- **First-boot credential handling** - a way for a plaintext password or
  Wi-Fi passphrase to end up on disk, in a log, or in the generated
  `firstrun.sh` in a form other than the intended `passlib` hash.
- **What gets executed inside the chroot** - a way to make the image build
  run something other than a target project's own real `build.sh`.
- **Path handling** - a path-traversal issue in how an output path, work
  directory, or config output directory is resolved.

please report it responsibly:

1. **Email**: Send a detailed report to `electrohobby3d@gmail.com`.
2. **Impact**: Describe the attack surface affected and a realistic
   scenario (this tool has no network-facing service of its own - it's a
   desktop/CLI tool a person runs by hand).
3. **Response**: Initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy.
