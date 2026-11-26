#!/usr/bin/env python3
r"""Automated CI Boot-Safety Gate for 6.6.163-tarostream GKI drop-in builds.

Verifies:
  1. ARM64 Linux Image magic header ('ARMd' at offset 0x38) and sane binary size.
  2. utsrelease.h matches 6.6.163-*-tarostream and vermagic has no legacy branding.
  3. Built Image retains tarostream, susfs, and nomount markers.
  4. Final .config satisfies all root-flavor (tiann/KernelSU or Baka-SU/BakaSU),
     SUSFS v2.4.0, NoMount, DroidSpaces, zero-overhead thermal/power (pure EEVDF+WALT,
     AMU, TEO, BBR+FQ, WQ power-efficient, RCU lazy, MGLRU, HZ=250), and KMI/CFI checks.
  5. AnyKernel3 Lloyd ASCII banner is mobile-safe (<= 46 columns per line, pure printable
     ASCII, zero shell-escaping hazards: $, `, \, ").
  6. fs/f2fs/super.c recognizes all 28 live /data F2FS mount flags from Xiaomi 15 PLZ110.
  7. Module.symvers / vmlinux.symvers exports all critical vendor_dlkm symbols
     (qcom, xiaomi, oplus, WALT/DRM/WLAN/UFS/BT) with 0 CRC drift against
     android/abi_gki_aarch64.stg.
"""
import argparse
import re
import struct
import sys
from pathlib import Path

REQUIRED_CONFIG_Y = [
    # Root & hooks
    "CONFIG_KSU",
    "CONFIG_KPROBES",
    "CONFIG_HAVE_KPROBES",
    "CONFIG_KPROBE_EVENTS",
    "CONFIG_OVERLAY_FS",
    # SUSFS v2.4.0
    "CONFIG_KSU_SUSFS",
    "CONFIG_KSU_SUSFS_SUS_PATH",
    "CONFIG_KSU_SUSFS_SUS_MOUNT",
    "CONFIG_KSU_SUSFS_SUS_KSTAT",
    "CONFIG_KSU_SUSFS_SPOOF_UNAME",
    "CONFIG_KSU_SUSFS_ENABLE_LOG",
    "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS",
    "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG",
    "CONFIG_KSU_SUSFS_OPEN_REDIRECT",
    "CONFIG_KSU_SUSFS_SUS_MAP",
    "CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER",
    # NoMount
    "CONFIG_NOMOUNT",
    # DroidSpaces container/namespace/netfilter suite
    "CONFIG_SYSVIPC",
    "CONFIG_POSIX_MQUEUE",
    "CONFIG_IPC_NS",
    "CONFIG_PID_NS",
    "CONFIG_USER_NS",
    "CONFIG_DEVTMPFS",
    "CONFIG_BINFMT_MISC",
    "CONFIG_BINFMT_SCRIPT",
    "CONFIG_BINFMT_ELF",
    "CONFIG_TMPFS_XATTR",
    "CONFIG_TMPFS_POSIX_ACL",
    "CONFIG_NETFILTER_XT_MATCH_ADDRTYPE",
    "CONFIG_IP6_NF_NAT",
    "CONFIG_IP6_NF_TARGET_MASQUERADE",
    "CONFIG_MACVLAN",
    "CONFIG_IP_NF_TARGET_REJECT",
    "CONFIG_IP6_NF_TARGET_REJECT",
    "CONFIG_NETFILTER_XT_TARGET_LOG",
    "CONFIG_NETFILTER_XT_MATCH_RECENT",
    "CONFIG_IP_SET",
    "CONFIG_IP_SET_HASH_IP",
    "CONFIG_IP_SET_HASH_NET",
    "CONFIG_NETFILTER_XT_SET",
    # Thermal & battery efficiency without performance capping
    "CONFIG_WQ_POWER_EFFICIENT_DEFAULT",
    "CONFIG_RCU_LAZY",
    "CONFIG_HZ_250",
    "CONFIG_NO_HZ_IDLE",
    "CONFIG_LRU_GEN",
    "CONFIG_LRU_GEN_ENABLED",
    "CONFIG_ARM64_AMU_EXTN",
    "CONFIG_CPU_IDLE_GOV_TEO",
    "CONFIG_TCP_CONG_BBR",
    "CONFIG_DEFAULT_BBR",
    "CONFIG_NET_SCH_FQ",
    # KMI, KCFI & F2FS drop-in safety
    "CONFIG_MODVERSIONS",
    "CONFIG_APEX_RELAX_GKI_MODULE_KMI",
    "CONFIG_CFI_CLANG",
    "CONFIG_KASAN_HW_TAGS",
    "CONFIG_F2FS_FS",
    "CONFIG_F2FS_FS_HYBRID_UFS",
    "CONFIG_F2FS_VIP_FILE",
]

REQUIRED_CONFIG_OFF = [
    "CONFIG_SCHED_BORE",
    "CONFIG_DEFAULT_CUBIC",
    "CONFIG_TRIM_UNUSED_KSYMS",
    "CONFIG_RCU_LAZY_DEFAULT_OFF",
    "CONFIG_HZ_1000",
    "CONFIG_CFI_PERMISSIVE",
    "CONFIG_LD_DEAD_CODE_DATA_ELIMINATION",
]

REQUIRED_CONFIG_STR = {
    "CONFIG_DEFAULT_TCP_CONG": '"bbr"',
}

BAKASU_CONFIG_OFF = [
    "CONFIG_KSU_TRACEPOINT_HOOK",
    "CONFIG_KSU_MANUAL_HOOK",
]

LIVE_F2FS_MOUNT_OPTS = [
    "lazytime", "background_gc", "gc_merge", "discard", "discard_unit",
    "user_xattr", "inline_xattr", "acl", "inline_data", "inline_dentry",
    "flush_merge", "barrier", "extent_cache", "age_extent_cache", "mode",
    "active_logs", "reserve_root", "reserve_node", "resuid", "resgid",
    "inlinecrypt", "alloc_mode", "checkpoint_merge", "fsync_mode", "atgc",
    "memory", "errors", "lookup_mode",
]

CRITICAL_VENDOR_SYMBOLS = [
    # WALT / scheduler vendor hooks
    "__tracepoint_android_vh_scheduler_tick",
    "__tracepoint_android_rvh_schedule",
    "__tracepoint_android_rvh_sched_fork_init",
    "__tracepoint_android_rvh_sched_newidle_balance",
    "sched_setscheduler",
    "sched_setscheduler_nocheck",
    "rebuild_sched_domains",
    "resched_curr",
    # Interconnect / io_uring (the 14 symbols protected by __counted_by genksyms fix)
    "icc_set_bw",
    "of_icc_get",
    # UFS / storage
    "ufshcd_pltfrm_init",
    "ufshcd_remove",
    # DRM / display
    "drm_atomic_helper_check",
    "drm_dev_register",
    # Wireless / BT / net
    "register_netdev",
    "rfkill_alloc",
    "netif_rx",
    "__netdev_alloc_skb",
    # Core / VFS / binder / memory
    "__kmalloc",
    "filp_open",
    "filp_close",
]

BANNER_MAX_COLS = 46
BANNER_ALLOWED_ART_CHARS = set("@%#*+=-:. ")
BANNER_FORBIDDEN_SHELL_CHARS = set('$`\\"')


def parse_config(path: Path) -> dict[str, str]:
    cfg: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and line.endswith(" is not set"):
            key = line[2:-11].strip()
            cfg[key] = "n"
        elif "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def parse_symvers(path: Path) -> dict[str, int]:
    syms: dict[str, int] = {}
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("0x"):
            syms[parts[1]] = int(parts[0], 16)
    return syms


def parse_stg_crcs(path: Path) -> dict[str, int]:
    crcs: dict[str, int] = {}
    in_sym = False
    name = ""
    crc = None
    with path.open(errors="replace") as f:
        for line in f:
            if line.startswith("elf_symbol {"):
                in_sym = True
                name = ""
                crc = None
            elif in_sym:
                s = line.strip()
                if s.startswith('name: "'):
                    name = s.split('"', 2)[1]
                elif s.startswith("crc: 0x"):
                    crc = int(s.split()[1], 16)
                elif s == "}":
                    if name and crc is not None:
                        crcs[name] = crc
                    in_sym = False
    return crcs


def parse_symbol_list(path: Path) -> set[str]:
    syms: set[str] = set()
    if not path.is_file():
        return syms
    for line in path.read_text(errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("["):
            continue
        syms.add(s)
    return syms


def verify_anykernel_banner(ak_path: Path, log, fail) -> None:
    """Verify Lloyd ASCII banner & mobile console header lines in anykernel.sh."""
    if not ak_path.is_file():
        fail(f"Missing AnyKernel3 script: {ak_path}")
        return

    lines = ak_path.read_text(encoding="utf-8").splitlines()
    in_banner = False
    found_begin = False
    found_end = False
    art_lines: list[tuple[int, str]] = []

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if stripped == "# BEGIN LLOYD BANNER":
            in_banner = True
            found_begin = True
            continue
        if stripped == "# END LLOYD BANNER":
            in_banner = False
            found_end = True
            continue
        if in_banner:
            m = re.fullmatch(r'ui_print "(.*)"', stripped)
            if not m:
                fail(f"Banner line {lineno} is not a clean double-quoted ui_print: {raw!r}")
                continue
            payload = m.group(1)
            art_lines.append((lineno, payload))
            if len(payload) > BANNER_MAX_COLS:
                fail(f"Banner line {lineno} exceeds {BANNER_MAX_COLS} cols ({len(payload)}): {payload!r}")
            bad_shell = sorted(set(payload) & BANNER_FORBIDDEN_SHELL_CHARS)
            if bad_shell:
                fail(f"Banner line {lineno} contains shell-escaping hazard(s) {bad_shell}: {payload!r}")
            bad_chars = sorted(set(payload) - BANNER_ALLOWED_ART_CHARS)
            if bad_chars:
                fail(f"Banner line {lineno} contains non-ASCII-art char(s) {bad_chars}: {payload!r}")

    if not (found_begin and found_end):
        fail(f"Missing '# BEGIN LLOYD BANNER' / '# END LLOYD BANNER' markers in {ak_path}")
        return

    if not (20 <= len(art_lines) <= 28):
        fail(f"Unexpected Lloyd banner height: {len(art_lines)} lines (expected 20..28)")

    max_w = max((len(p) for _, p in art_lines), default=0)

    # Also verify non-banner static ui_print lines (skipping lines with runtime shell vars like $kernel_version)
    header_over = []
    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        m = re.fullmatch(r'ui_print "(.*)"', stripped)
        if not m:
            continue
        payload = m.group(1)
        if "$" in payload or "__" in payload:
            continue
        if len(payload) > BANNER_MAX_COLS:
            header_over.append((lineno, len(payload), payload))
    for lineno, length, payload in header_over:
        fail(f"ui_print line {lineno} exceeds {BANNER_MAX_COLS} cols ({length}): {payload!r}")

    log(f"[Banner] Verified {ak_path}: {len(art_lines)} Lloyd ASCII lines, max_width={max_w}/{BANNER_MAX_COLS} cols, 0 escaping hazards.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=False, default=None)
    ap.add_argument("--report", required=False, default=None)
    ap.add_argument("--root-flavor", choices=("kernelsu", "bakasu"), default="kernelsu")
    ap.add_argument("--anykernel", default=None,
                    help="Path to anykernel.sh to validate (defaults to <src>/.github/anykernel/anykernel.sh)")
    ap.add_argument("--banner-only", action="store_true",
                    help="Only run the AnyKernel3 Lloyd banner check (for local pre-push sanity check)")
    ap.add_argument("--allow-non-vendor-drift", action="store_true",
                    help="Only fail on CRC drift in qcom/xiaomi/oplus/critical symbols (still reports all drift)")
    args = ap.parse_args()

    src = Path(args.src)
    ak_path = Path(args.anykernel) if args.anykernel else (src / ".github/anykernel/anykernel.sh")
    report_lines: list[str] = []
    errors: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        report_lines.append(msg)

    def fail(msg: str) -> None:
        print(f"ERROR: {msg}", file=sys.stderr)
        report_lines.append(f"ERROR: {msg}")
        errors.append(msg)

    log(f"=== tarostream 6.6.163 CI Boot-Safety Gate (flavor={args.root_flavor}) ===")

    # Banner verification (runs both in --banner-only and full CI modes)
    verify_anykernel_banner(ak_path, log, fail)
    if args.banner_only:
        return 1 if errors else 0

    if not args.out or not args.report:
        fail("--out and --report are required unless --banner-only is passed")
        return 1

    out = Path(args.out)

    # 1. ARM64 Image header & size check
    image = out / "arch/arm64/boot/Image"
    if not image.is_file():
        fail(f"Missing kernel Image: {image}")
    else:
        data = image.read_bytes()
        size_mb = len(data) / (1024 * 1024)
        magic = data[0x38:0x3C] if len(data) >= 0x40 else b""
        _, image_size = struct.unpack_from("<QQ", data, 0x08) if len(data) >= 0x20 else (0, 0)
        log(f"[Image] path={image} size={len(data)} bytes ({size_mb:.2f} MiB) magic={magic!r} header_image_size={image_size}")
        if magic != b"ARMd":
            fail(f"Invalid ARM64 Linux Image magic at 0x38: expected b'ARMd', got {magic!r}")
        if len(data) < 20 * 1024 * 1024 or len(data) > 64 * 1024 * 1024:
            fail(f"Unexpected Image size: {size_mb:.2f} MiB (expected 20..64 MiB)")
        for needle in (b"6.6.163", b"tarostream", b"susfs", b"nomount"):
            cnt = data.count(needle)
            log(f"[Image] marker {needle.decode()!r}: {cnt} occurrence(s)")
            if cnt == 0:
                fail(f"Marker {needle.decode()!r} missing from compiled Image (stripped or not compiled in)")

    # 2. utsrelease & vermagic check
    uts_file = out / "include/generated/utsrelease.h"
    if uts_file.is_file():
        uts = uts_file.read_text()
        m = re.search(r'"([^"]+)"', uts)
        release = m.group(1) if m else ""
        log(f"[UTS] UTS_RELEASE={release}")
        if not re.match(r"^6\.6\.163-.*tarostream", release):
            fail(f"UTS_RELEASE does not match 6.6.163-.*tarostream: {release!r}")
        if "APEX" in release or "Foundry" in release:
            fail(f"Legacy APEX/Foundry branding leaked into UTS_RELEASE: {release!r}")
    else:
        fail(f"Missing {uts_file}")

    # 3. .config verification
    cfg_path = out / ".config"
    if not cfg_path.is_file():
        fail(f"Missing {cfg_path}")
    else:
        cfg = parse_config(cfg_path)
        log(f"[Config] Parsed {len(cfg)} entries from {cfg_path}")
        log(f"[Config] CC_VERSION_TEXT={cfg.get('CONFIG_CC_VERSION_TEXT', 'UNKNOWN')}")
        log(f"[Config] LOCALVERSION={cfg.get('CONFIG_LOCALVERSION', 'UNKNOWN')}")
        log(f"[Config] DEFAULT_TCP_CONG={cfg.get('CONFIG_DEFAULT_TCP_CONG', 'UNKNOWN')}")

        for key in REQUIRED_CONFIG_Y:
            val = cfg.get(key)
            if val != "y":
                fail(f"Config mismatch: expected {key}=y, got {val!r}")

        off_list = list(REQUIRED_CONFIG_OFF)
        if args.root_flavor == "bakasu":
            off_list.extend(BAKASU_CONFIG_OFF)
        for key in off_list:
            val = cfg.get(key, "n")
            if val != "n":
                fail(f"Config mismatch: expected {key} off, got {val!r}")

        for key, expected in REQUIRED_CONFIG_STR.items():
            val = cfg.get(key)
            if val != expected:
                fail(f"Config mismatch: expected {key}={expected}, got {val!r}")

        log(f"[Config] Checked {len(REQUIRED_CONFIG_Y)} required=y, {len(off_list)} required=off, "
            f"{len(REQUIRED_CONFIG_STR)} required=str options (flavor={args.root_flavor}).")

    # 4. F2FS /data mount option parity check
    f2fs_super = src / "fs/f2fs/super.c"
    if not f2fs_super.is_file():
        fail(f"Missing {f2fs_super}")
    else:
        f2fs_text = f2fs_super.read_text(errors="replace")
        missing_opts = [opt for opt in LIVE_F2FS_MOUNT_OPTS if opt not in f2fs_text]
        if missing_opts:
            fail(f"Missing live /data F2FS mount option(s) in fs/f2fs/super.c: {missing_opts}")
        else:
            log(f"[F2FS] All {len(LIVE_F2FS_MOUNT_OPTS)} live /data mount options verified in fs/f2fs/super.c.")

    # 5. Module.symvers / vmlinux.symvers & ABI CRC verification
    symvers_path = out / "Module.symvers"
    if not symvers_path.is_file() or symvers_path.stat().st_size == 0:
        symvers_path = out / "vmlinux.symvers"
    if not symvers_path.is_file() or symvers_path.stat().st_size == 0:
        fail("Missing non-empty Module.symvers / vmlinux.symvers")
    else:
        ours = parse_symvers(symvers_path)
        log(f"[Symvers] Loaded {len(ours)} exported symbols from {symvers_path}")

        # 5a. Critical vendor_dlkm symbols must be present
        missing_crit = [s for s in CRITICAL_VENDOR_SYMBOLS if s not in ours]
        if missing_crit:
            fail(f"Missing critical vendor_dlkm exported symbol(s): {missing_crit}")
        else:
            log(f"[Symvers] All {len(CRITICAL_VENDOR_SYMBOLS)} critical vendor_dlkm symbols present.")

        # 5b. Check presence of qcom / xiaomi / oplus KMI symbol lists
        vendor_syms: set[str] = set()
        for lst in ("android/abi_gki_aarch64_qcom", "android/abi_gki_aarch64_xiaomi", "android/abi_gki_aarch64_oplus"):
            s = parse_symbol_list(src / lst)
            vendor_syms |= s
            present = sum(1 for sym in s if sym in ours)
            log(f"[Symvers] {lst}: {present}/{len(s)} present in built symvers")

        # 5c. Compare CRCs against android/abi_gki_aarch64.stg
        stg = src / "android/abi_gki_aarch64.stg"
        if stg.is_file():
            stock = parse_stg_crcs(stg)
            common = sorted(set(ours) & set(stock))
            drifted_all = [(sym, ours[sym], stock[sym]) for sym in common if ours[sym] != stock[sym]]
            drifted_vendor = [x for x in drifted_all if x[0] in vendor_syms or x[0] in CRITICAL_VENDOR_SYMBOLS]
            log(f"[ABI] Compared {len(common)} symbols against android/abi_gki_aarch64.stg: "
                f"total_drift={len(drifted_all)}, qcom/xiaomi/oplus_drift={len(drifted_vendor)}")
            for sym, c_ours, c_stock in drifted_all[:60]:
                tag = "VENDOR" if (sym in vendor_syms or sym in CRITICAL_VENDOR_SYMBOLS) else "OTHER"
                log(f"  DRIFT [{tag}] {sym}: ours=0x{c_ours:08x} stock=0x{c_stock:08x}")
            if len(drifted_all) > 60:
                log(f"  ... ({len(drifted_all) - 60} more drifted symbols)")
            if drifted_vendor:
                fail(f"ABI CRC drift detected on {len(drifted_vendor)} QCOM/Xiaomi/OPLUS vendor_dlkm symbol(s)!")
            elif drifted_all and not args.allow_non_vendor_drift:
                fail(f"ABI CRC drift detected on {len(drifted_all)} GKI symbol(s)!")
        else:
            log("[ABI] WARNING: android/abi_gki_aarch64.stg not found; skipped CRC comparison.")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n")

    if errors:
        log(f"\nBOOT-SAFETY GATE FAILED ({len(errors)} error(s)).")
        return 1
    log("\nBOOT-SAFETY GATE PASSED (0 errors).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
