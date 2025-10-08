#!/usr/bin/env python3
"""
usb_writer.py

Cross-platform (Linux/macOS/Windows) helper to:
- list removable disks
- optionally wipe/format a target disk with GPT or MBR
- write an ISO image to the target (raw write)

WARNING: This script WILL ERASE the selected target device. Use only on devices you own.

Limitations / Notes:
- On Unix (Linux/macOS) it uses `lsblk`/`diskutil`, `parted`/`sgdisk` and `dd`.
- On Windows it shells out to PowerShell's Get-Disk and uses diskpart to format; raw write is not provided natively here (recommend using Rufus/win32-imager for complex Windows flows).
- Must be run as root/Administrator.

This script is provided as an example and starting point for a safer GUI/tool. Always review commands before running.

Usage examples:
  sudo python3 usb_writer.py --list
  sudo python3 usb_writer.py --target /dev/sdb --iso linux.iso --parttable gpt --format ext4
  python usb_writer.py --list  # on Windows run in elevated PowerShell

"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_root():
    if platform.system() in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            sys.exit("This script must be run as root (sudo). Exiting.")
    elif platform.system() == "Windows":
        # On Windows, best-effort admin check
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                sys.exit("Please run this script from an elevated Administrator PowerShell. Exiting.")
        except Exception:
            pass


# --------- Disk listing helpers ---------
def list_disks_unix():
    # Prefer lsblk for Linux
    try:
        out = subprocess.check_output(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,TRAN"], text=True)
        print(out)
        return
    except Exception:
        pass
    # Fallback to /proc/partitions
    try:
        out = subprocess.check_output(["cat", "/proc/partitions"], text=True)
        print(out)
    except Exception as e:
        print("Failed to list disks:", e)


def list_disks_mac():
    try:
        out = subprocess.check_output(["diskutil", "list"], text=True)
        print(out)
    except Exception as e:
        print("Failed to list disks with diskutil:", e)


def list_disks_windows():
    # Use PowerShell Get-Disk
    try:
        cmd = ["powershell", "-Command", "Get-Disk | Format-Table -AutoSize"]
        out = subprocess.check_output(cmd, text=True)
        print(out)
    except Exception as e:
        print("Failed to list disks via PowerShell:", e)


def list_disks():
    system = platform.system()
    print(f"Detected OS: {system}\n")
    if system == "Linux":
        list_disks_unix()
    elif system == "Darwin":
        list_disks_mac()
    elif system == "Windows":
        list_disks_windows()
    else:
        print("Unsupported OS for automatic disk listing")


# --------- Partition table creation ---------
def create_partition_table_unix(device, table):
    # table: 'gpt' or 'mbr'
    if shutil.which("sgdisk"):
        if table == "gpt":
            cmd = ["sgdisk", "--zap-all", device]
        else:
            # write MBR using sgdisk conversion
            cmd = ["sgdisk", "--mbrtogpt=1", device]
            # note: --mbrtogpt converts MBR->GPT; forcing MBR creation is easier with parted
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            print("sgdisk failed:", e)
    elif shutil.which("parted"):
        try:
            subprocess.check_call(["parted", "-s", device, "mklabel", table])
        except subprocess.CalledProcessError as e:
            print("parted failed:", e)
    else:
        raise SystemExit("Neither sgdisk nor parted found. Install parted (or gdisk) and retry.")


def format_partition_unix(device, fs_type="ext4"):
    # For simplicity, create a single partition spanning entire disk then format it
    # device example: /dev/sdb -> partition /dev/sdb1 (Linux) or /dev/disk2 -> /dev/disk2s1 (mac)
    # We'll use parted to make a primary partition
    if not shutil.which("parted"):
        raise SystemExit("parted not available. Install parted and retry.")
    try:
        subprocess.check_call(["parted", "-s", device, "mkpart", "primary", fs_type, "0%", "100%"])
    except subprocess.CalledProcessError as e:
        print("Failed to create partition:", e)
        return
    # Find partition path (simple heuristic)
    part = None
    if platform.system() == "Linux":
        part = device + "1"
    elif platform.system() == "Darwin":
        # macOS naming: /dev/disk2 -> /dev/disk2s1
        part = device + "s1"
    else:
        raise SystemExit("Unsupported OS for formatting partitions via this script")
    # Wait a moment for kernel to settle
    subprocess.call(["sleep", "1"]) if platform.system() != "Windows" else None
    # Format
    if fs_type in ("ext4", "ext3", "ext2"):
        mkcmd = ["mkfs." + fs_type, part]
    elif fs_type in ("vfat", "fat32"):
        mkcmd = ["mkfs.vfat", part]
    elif fs_type == "ntfs":
        mkcmd = ["mkfs.ntfs", part]
    else:
        raise SystemExit("Unsupported filesystem: " + fs_type)
    try:
        subprocess.check_call(mkcmd)
    except subprocess.CalledProcessError as e:
        print("mkfs failed:", e)


def write_iso_unix(device, iso_path):
    # Use dd for raw writing. This will overwrite entire device.
    if not Path(iso_path).exists():
        raise SystemExit("ISO file not found: " + iso_path)
    bs = "4M"
    conv = "status=progress conv=fsync"
    cmd = ["dd", f"if={iso_path}", f"of={device}", f"bs={bs}", conv]
    print("Running:", " ".join(cmd))
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print("dd failed:", e)


def write_iso_windows(device_number, iso_path):
    # Windows: recommend using external tools like Rufus or Win32 Disk Imager for raw ISO->USB.
    raise SystemExit("Windows raw write not implemented. Use Rufus or Win32 Disk Imager on Windows.")


# --------- Confirmation helper ---------

def confirm(target):
    print("\n!!! WARNING !!!")
    print(f"About to erase/modify device: {target}")
    print("This action is destructive and irreversible. Make sure you selected the correct device.")
    ans = input("Type the device path (or 'YES' to confirm): ")
    if ans != target and ans != "YES":
        print("Confirmation failed. Aborting.")
        sys.exit(1)


# --------- CLI ---------

def main():
    parser = argparse.ArgumentParser(description="USB/ISO writer helper (example script). Use carefully.")
    parser.add_argument("--list", action="store_true", help="List removable disks")
    parser.add_argument("--target", help="Target device (e.g. /dev/sdb or disk number on Windows)")
    parser.add_argument("--iso", help="Path to ISO file to write (raw write)")
    parser.add_argument("--parttable", choices=["gpt", "mbr"], help="Partition table to create before writing (optional)")
    parser.add_argument("--format", help="Create partition and format with FS (ext4, vfat, ntfs) after making parttable")
    parser.add_argument("--yes", action="store_true", help="Assume yes for confirmations (dangerous)")

    args = parser.parse_args()

    if args.list:
        list_disks()
        return

    if not args.target:
        parser.error("--target is required unless --list is used")

    check_root()
    system = platform.system()
    target = args.target

    if not args.yes:
        confirm(target)

    # If user asked to create partition table
    if args.parttable:
        if system in ("Linux", "Darwin"):
            print(f"Creating partition table {args.parttable} on {target}")
            create_partition_table_unix(target, args.parttable)
            if args.format:
                format_partition_unix(target, args.format)
        elif system == "Windows":
            print("Windows partitioning/formatting path")
            # Create diskpart script
            ps = f"select disk {target}\nclean\nconvert {args.parttable}\ncreate partition primary\nformat fs={args.format} quick\nassign\nexit\n"
            print("Running diskpart script (requires admin)")
            pfile = "/tmp/diskpart_script.txt" if platform.system() != "Windows" else "diskpart_script.txt"
            with open(pfile, "w") as f:
                f.write(ps)
            try:
                subprocess.check_call(["diskpart", "/s", pfile])
            except Exception as e:
                print("diskpart failed:", e)

    # If user asked to write ISO raw
    if args.iso:
        if system in ("Linux", "Darwin"):
            write_iso_unix(target, args.iso)
        elif system == "Windows":
            write_iso_windows(target, args.iso)

    print("Done. Remember to safely eject the device.")


if __name__ == "__main__":
    main()
