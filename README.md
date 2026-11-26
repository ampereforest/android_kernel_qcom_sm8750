# tarostream (`6.6.163-tarostream`)

GKI drop-in kernel for **Xiaomi 15 (`dada`, SM8750 / Snapdragon 8 Elite)** running **ColorOS 17 V6 `v7.3.1` (`PLZ110` base)** with unmodified stock `/vendor_dlkm` and `/system_dlkm` kernel modules.

## Architecture & Feature Stack

- **Kernel Base:** AOSP `android15-6.6-lts` **`6.6.163`** (`75935bb82f02`) 3-way merged onto `ilertnost/android_kernel_qcom_sm8750` (`lineage-23.2` / `v1.4-newbase`) to preserve Google GKI KMI struct layout padding and SM8750 drop-in fixes (UFS `dev_cmd` completion reinit, EROFS LZ4 inplace `>> 6` margin, F2FS VIP & MAIN/EXT hybrid UFS, DRM self-relaxing valid-clones check, Oryon ARMv9.2-A ISA targeting, `__counted_by` genksyms guard).
- **Root:** Official **`tiann/KernelSU`** (`main`, latest GitHub Actions commit — dynamically fetched and versioned at build time in CI, `KSU_VERSION >= 32736`).
- **Stealth & Path Redirection:**
  - **SUSFS v2.4.0** (`simonpunk/susfs4ksu` `gki-android15-6.6`, including `CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y`).
  - **NoMount** (`maxsteeel/nomount` `dev`, built-in `fs/nomount/`).
- **Containerization (DroidSpaces):**
  - Full `r24` DroidSpaces config set (`SYSVIPC`, `POSIX_MQUEUE`, `IPC_NS`, `PID_NS`, `USER_NS`, `DEVTMPFS`, `BINFMT_MISC`, `OVERLAY_FS`, `TMPFS_XATTR`, `TMPFS_POSIX_ACL`, `MACVLAN`, `IP_SET`, `IP6_NF_NAT`, `IP6_NF_TARGET_MASQUERADE`, `IP_NF_TARGET_REJECT`, `IP6_NF_TARGET_REJECT`, `NETFILTER_XT_*`) backed by KMI-safe `ANDROID_KABI_USE` SYSVIPC padding and the `oplus_bsp_midas` ghost-task guard.
- **Thermal & Idle Efficiency (Zero Peak Performance Cap):**
  - `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`
  - `CONFIG_RCU_LAZY=y` with `CONFIG_RCU_LAZY_DEFAULT_OFF` disabled
  - `CONFIG_HZ_250=y` (`NO_HZ_IDLE`), MGLRU (`CONFIG_LRU_GEN=y`, `CONFIG_LRU_GEN_ENABLED=y`)
  - Preserves stock `sched_walt.ko` `/proc/sys/walt/*` interface and uncapped CPU (`3.53/4.32 GHz`) / GPU (`1,100 MHz`) clocks.
- **KMI Drop-In Hardening:**
  - `CONFIG_MODVERSIONS=y`, `# CONFIG_TRIM_UNUSED_KSYMS is not set`, `CONFIG_APEX_RELAX_GKI_MODULE_KMI=y`, `CONFIG_CFI_CLANG=y`, `android/abi_gki_protected_exports_*` removed, `modules.bzl` `protected_modules = []`, `BUILD.bazel` relaxed.

## CI Build (GitHub Actions)

Workflow: [`.github/workflows/build-tarostream.yml`](.github/workflows/build-tarostream.yml)

1. Frees runner disk space and downloads the latest compatible AOSP prebuilt Clang toolchain (`clang-r614150` / `clang-r547379`).
2. Fetches latest `tiann/KernelSU` (`main`), computes live `KSU_VERSION`, and applies SUSFS integration.
3. Builds `6.6.163-4k-tarostream` (`Image` + `Module.symvers`).
4. Runs the automated **CI Boot-Safety Gate** (`.github/scripts/verify_boot_safety.py`): verifies ARM64 `Image` magic header, `utsrelease`/`vermagic`, mandatory `.config` flags, all 27 live `/data` F2FS mount flags, and `Module.symvers` CRC/symbol parity against `android/abi_gki_aarch64.stg` + QCOM/Xiaomi/OPLUS symbol lists.
5. Packages `AnyKernel3-tarostream-6.6.163-<sha>.zip` (boot-only `Image` drop-in) as a GitHub Actions artifact.

## Credits

- [ilertnost/android_kernel_qcom_sm8750](https://github.com/ilertnost/android_kernel_qcom_sm8750) (SM8750 GKI drop-in foundation)
- [tiann/KernelSU](https://github.com/tiann/KernelSU)
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)
- [maxsteeel/nomount](https://github.com/maxsteeel/nomount)
- [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS)
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) & [WildKernels/AnyKernel3](https://github.com/WildKernels/AnyKernel3)
