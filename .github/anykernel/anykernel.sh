### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers
## tarostream 6.6.163 GKI Drop-In Installer (Xiaomi 15 dada / SM8750)

### AnyKernel setup
# global properties
properties() { '
kernel.string=tarostream 6.6.163 (__ROOT_NAME__ + SUSFS + NoMount + DroidSpaces)
do.devicecheck=0
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
do.check_boot_version=0
device.name1=dada
device.name2=PLZ110
device.name3=
device.name4=
device.name5=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
keycheck.timeout=10
'; } # end properties

### AnyKernel install
## boot shell variables
block=boot
is_slot_device=auto
ramdisk_compression=auto
patch_vbmeta_flag=auto
no_magisk_check=1

# import functions/variables and setup patching - see for reference (DO NOT REMOVE)
. tools/ak3-core.sh

# GKI 6.6 safety check
kernel_version=$(cat /proc/version | awk -F '-' '{print $1}' | awk '{print $3}')
case $kernel_version in
    6.6*) gki_supported=true ;;
    *) gki_supported=false ;;
esac

ui_print " "
# BEGIN LLOYD BANNER
ui_print "           .=- :--====+==-:.                 "
ui_print "           :-=====++++++*#*#%+-:             "
ui_print "           -==++++++**+++**++++++=:.         "
ui_print "        .--+++*#**+++++==============-:..    "
ui_print "       :***+++*+++-===: -=.==-=====:-=::..   "
ui_print "       **+++++===-==::=+.=.-=-:-====..::     "
ui_print "      =++++-====::: ::%#-=.:=- :.=.+=.       "
ui_print "    .-==--::---=:..++=##%:..=* ..-.--:       "
ui_print "   .-:....:-.::-..:+-=.*@-:.=#=+ .::::       "
ui_print "     .::::.. ..:.:%@-=-@#%+-*-.:..:::.       "
ui_print "      .:::.==+ ..:#@@@@@@@%@*-=*..::.        "
ui_print "       ..:.* #*--:#@@@@@@@@@%@@#.:..         "
ui_print "         . .=*%@@@@@@@@@@@@@@@%:             "
ui_print "      ......   .*@@%@@@@@#*@@@@-..==.    ..  "
ui_print "       .:..=+=.:+@@%@@@@@@@@@#-  .-##+..=#*. "
ui_print "           *=-#@@@@%:=*#@@%#*.     =##: :**+ "
ui_print "           ====:-=*#-    ##%%#:    -*#++%+*= "
ui_print "         ::::-:.    == :+*++-.   :*%%%%@%##= "
ui_print "       +@@@%%*==-:-..:-++=*-:=*: +%%%=-:+#**="
ui_print "      -=%%%##%#::.:%#:..:%=*::*#-*####%##*=--"
ui_print "      .=%%%#-:+==*=:%*:-=++=-::*#:+######*##*"
ui_print "      .+####%#-=+**+==:.--:.=++=#+:=**=-+*+=:"
ui_print "       =#####%%#*++=++**.:=:=+++-#=#+*****=  "
ui_print "       -*:++=:..:-=-=:=++---=+=+=--:=+++++=  "
# END LLOYD BANNER
ui_print "=============================================="
ui_print "  tarostream 6.6.163 (Xiaomi 15 / SM8750)"
ui_print "  Root  : __ROOT_LINE__"
ui_print "  Stack : SUSFS 2.4 + NoMount + DroidSpaces"
ui_print "  Sched : EEVDF+WALT | BBR+FQ | TEO | AMU"
ui_print "  Build : __BUILD_SHA__ (__CLANG_VER__)"
ui_print "=============================================="
ui_print "  Running: $kernel_version (ok: $gki_supported)"
$gki_supported || abort "  -> Non-6.6 kernel ($kernel_version), abort."

# boot install (Image-only drop-in; preserves stock vendor_boot & vendor_dlkm)
split_boot

if [ -f "$SPLITIMG/ramdisk.cpio" ]; then
    unpack_ramdisk
    write_boot
else
    flash_boot
fi

ui_print " "
ui_print "  -> tarostream 6.6.163 flashed to boot!"
ui_print "  -> Stock vendor_boot & vendor_dlkm kept."
ui_print " "
