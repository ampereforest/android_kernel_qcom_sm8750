# tarostream (`6.6.163-tarostream`)

GKI drop-in kernel for **Xiaomi 15 (`dada`, SM8750 / Snapdragon 8 Elite)** running **ColorOS 17 V6 `v7.3.1` (`PLZ110` base)** with unmodified stock `/vendor_dlkm` and `/system_dlkm` kernel modules.

## Architecture & Feature Stack

- **Kernel Base:** AOSP `android15-6.6-lts` **`6.6.163`** (`75935bb82f02`) 3-way merged onto `ilertnost/android_kernel_qcom_sm8750` (`lineage-23.2` / `v1.4-newbase`) to preserve Google GKI KMI struct layout padding and SM8750 drop-in fixes (UFS `dev_cmd` completion reinit, EROFS LZ4 inplace `>> 6` margin, F2FS VIP & MAIN/EXT hybrid UFS, DRM self-relaxing valid-clones check, Oryon ARMv9.2-A ISA targeting, `__counted_by` genksyms guard).
- **Dual Root Flavors (Parallel GitHub Actions Matrix):**
  - **`kernelsu`:** Official **`tiann/KernelSU`** (`main`, dynamically fetched & versioned at build time) + matching **KernelSU Manager APK** bundled alongside the AnyKernel3 ZIP.
  - **`bakasu`:** Official **`Baka-SU/BakaSU`** (`main`, native SUSFS inline hooks) + matching **BakaSU Manager APK** (`arm64-v8a`) bundled alongside the AnyKernel3 ZIP.
- **Stealth & Path Redirection:**
  - **SUSFS v2.4.0** (`simonpunk/susfs4ksu` `gki-android15-6.6`, all 11 `CONFIG_KSU_SUSFS_*` options including `CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y`).
  - **NoMount** (`maxsteeel/nomount` `dev`, built-in `fs/nomount/`).
- **Containerization (DroidSpaces):**
  - Full `r24` DroidSpaces config set (`SYSVIPC`, `POSIX_MQUEUE`, `IPC_NS`, `PID_NS`, `USER_NS`, `DEVTMPFS`, `BINFMT_MISC`, `OVERLAY_FS`, `TMPFS_XATTR`, `TMPFS_POSIX_ACL`, `MACVLAN`, `IP_SET`, `IP6_NF_NAT`, `IP6_NF_TARGET_MASQUERADE`, `IP_NF_TARGET_REJECT`, `IP6_NF_TARGET_REJECT`, `NETFILTER_XT_*`) backed by KMI-safe `ANDROID_KABI_USE` SYSVIPC padding and the `oplus_bsp_midas` ghost-task guard.
- **Zero-Overhead Thermal & Power Efficiency (Uncapped Clocks):**
  - **Pure upstream Linux 6.6 EEVDF + Qualcomm WALT** (`# CONFIG_SCHED_BORE is not set`) — eliminates routine UI burst-inflation while keeping full WALT scaling, ColorOS CPU boost, and uncapped `3.53/4.32 GHz` CPU & `1,100 MHz` GPU clocks.
  - **ARMv9.2 Activity Monitors Unit** (`CONFIG_ARM64_AMU_EXTN=y`) for zero-CPU-overhead hardware frequency/cycle accounting.
  - **Timer Events Oriented CPUIdle** (`CONFIG_CPU_IDLE_GOV_TEO=y`) alongside Qualcomm `qcom-cpu-lpm`.
  - **TCP BBR + FQ Pacing by Default** (`CONFIG_TCP_CONG_BBR=y`, `CONFIG_DEFAULT_BBR=y`, `CONFIG_NET_SCH_FQ=y`) for lower modem active time and faster cellular/Wi-Fi tail recovery.
  - `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`, `CONFIG_RCU_LAZY=y` (`CONFIG_RCU_LAZY_DEFAULT_OFF` disabled), `CONFIG_HZ_250=y` (`NO_HZ_IDLE`), MGLRU (`CONFIG_LRU_GEN=y`, `CONFIG_LRU_GEN_ENABLED=y`).
- **KMI Drop-In Hardening:**
  - `CONFIG_MODVERSIONS=y`, `# CONFIG_TRIM_UNUSED_KSYMS is not set`, `CONFIG_APEX_RELAX_GKI_MODULE_KMI=y`, `CONFIG_CFI_CLANG=y`, `android/abi_gki_protected_exports_*` removed, `modules.bzl` `protected_modules = []`, `BUILD.bazel` relaxed.

## CI Build (GitHub Actions)

Workflow: [`.github/workflows/build-tarostream.yml`](.github/workflows/build-tarostream.yml)

Runs two parallel `ubuntu-24.04` runners (`kernelsu` and `bakasu`) sharing cached AOSP `clang-r614150`:
1. Integrates latest upstream root sources (`tiann/KernelSU` `main` or `Baka-SU/BakaSU` `main`) with SUSFS v2.4.0.
2. Compiles `6.6.163-4k-tarostream` (`Image` + `Module.symvers`).
3. Auto-fetches & integrity-verifies the matching Manager APK (`KernelSU-Manager-*.apk` / `BakaSU-Manager-*.apk`).
4. Runs the automated **CI Boot-Safety Gate** (`.github/scripts/verify_boot_safety.py`): verifies ARM64 `Image` magic header, `utsrelease`, mandatory `.config` flags, mobile-safe Lloyd ASCII banner (`<= 46` columns, zero shell-escaping hazards), all 28 live `/data` F2FS mount flags, and **`9593/9593` (`total_drift=0`)** ABI CRC parity against `android/abi_gki_aarch64.stg`.
5. Uploads `AnyKernel3-tarostream-6.6.163-{kernelsu,bakasu}-<short_sha>` containing the flashable ZIP, `.sha256`, `.config`, `boot-safety-report.txt`, and matching Manager APK.

## Credits

- [ilertnost/android_kernel_qcom_sm8750](https://github.com/ilertnost/android_kernel_qcom_sm8750) (SM8750 GKI drop-in foundation)
- [tiann/KernelSU](https://github.com/tiann/KernelSU) & [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU)
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)
- [maxsteeel/nomount](https://github.com/maxsteeel/nomount)
- [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS)
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) & [WildKernels/AnyKernel3](https://github.com/WildKernels/AnyKernel3)
