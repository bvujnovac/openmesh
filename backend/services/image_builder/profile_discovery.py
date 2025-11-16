"""
OpenWrt profile discovery.

Queries the ImageBuilder to discover all available device profiles
for a given target/subtarget combination.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from backend.core.config import settings


@dataclass
class DeviceProfile:
    """Discovered device profile from ImageBuilder."""

    profile: str
    title: str
    packages: List[str]


def discover_profiles(
    target: str,
    subtarget: str,
    version: str = "23.05.2",
) -> List[Dict[str, Any]]:
    """
    Discover available device profiles from OpenWrt ImageBuilder.

    Args:
        target: OpenWrt target (e.g., "ath79")
        subtarget: OpenWrt subtarget (e.g., "generic")
        version: OpenWrt version (default: "23.05.2")

    Returns:
        List of discovered profiles with metadata

    Example output:
        [
            {
                "profile": "ubnt_nanostation-m",
                "title": "Ubiquiti NanoStation M (XM)",
                "packages": [],
            },
            {
                "profile": "ubnt_nanostation-m-xw",
                "title": "Ubiquiti NanoStation M (XW)",
                "packages": ["kmod-ath10k"],
            },
            ...
        ]
    """
    # ImageBuilder directory
    ib_name = f"openwrt-imagebuilder-{version}-{target}-{subtarget}.Linux-x86_64"
    ib_dir = Path(settings.IMAGEBUILDER_PATH) / ib_name

    # Check if ImageBuilder exists, download if needed
    if not ib_dir.exists():
        try:
            _download_imagebuilder(target, subtarget, version)
        except Exception:
            # If download fails, return empty list
            # User can still build, ImageBuilder will download during build
            return []

    try:
        # Run: make info
        result = subprocess.run(
            ["make", "info"],
            cwd=ib_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        # Parse output
        profiles = _parse_imagebuilder_info(result.stdout)
        return profiles

    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _download_imagebuilder(target: str, subtarget: str, version: str) -> Path:
    """
    Download OpenWrt ImageBuilder if not present.

    Args:
        target: OpenWrt target (e.g., "ath79")
        subtarget: OpenWrt subtarget (e.g., "generic")
        version: OpenWrt version (e.g., "23.05.2")

    Returns:
        Path to ImageBuilder directory

    Raises:
        RuntimeError: If download fails
    """
    # ImageBuilder naming
    ib_name = f"openwrt-imagebuilder-{version}-{target}-{subtarget}.Linux-x86_64"
    ib_dir = Path(settings.IMAGEBUILDER_PATH) / ib_name
    ib_archive = Path(settings.IMAGEBUILDER_PATH) / f"{ib_name}.tar.xz"

    # Ensure base directory exists
    Path(settings.IMAGEBUILDER_PATH).mkdir(parents=True, exist_ok=True)

    # Check if already exists
    if ib_dir.exists():
        return ib_dir

    # Download URL
    download_url = (
        f"https://downloads.openwrt.org/releases/{version}/targets/"
        f"{target}/{subtarget}/{ib_name}.tar.xz"
    )

    try:
        # Download
        subprocess.run(
            ["wget", "-O", str(ib_archive), download_url],
            check=True,
            capture_output=True,
            text=True,
        )

        # Extract
        subprocess.run(
            ["tar", "-xJf", str(ib_archive), "-C", str(settings.IMAGEBUILDER_PATH)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Cleanup archive
        ib_archive.unlink()

        return ib_dir

    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to download ImageBuilder: {e.stderr if e.stderr else str(e)}"
        raise RuntimeError(error_msg)


def _parse_imagebuilder_info(output: str) -> List[Dict[str, Any]]:
    """
    Parse 'make info' output from ImageBuilder.

    Example output format:
        Available Profiles:

        ubnt_nanostation-m:
            Ubiquiti NanoStation M (XM)
            Packages:

        ubnt_nanostation-m-xw:
            Ubiquiti NanoStation M (XW)
            Packages: kmod-ath10k ath10k-firmware-qca988x-ct

        ...
    """
    profiles = []
    lines = output.split("\n")

    current_profile = None
    current_title = None
    current_packages = []

    in_profiles_section = False

    for line in lines:
        line = line.rstrip()

        # Detect start of profiles section
        if "Available Profiles:" in line or "Default Packages:" in line:
            in_profiles_section = "Available Profiles:" in line
            continue

        if not in_profiles_section:
            continue

        # Profile definition (no leading whitespace, ends with ':')
        if line and not line[0].isspace() and line.endswith(":"):
            # Save previous profile
            if current_profile:
                profiles.append({
                    "profile": current_profile,
                    "title": current_title or current_profile,
                    "packages": current_packages,
                })

            # Start new profile
            current_profile = line[:-1].strip()  # Remove trailing ':'
            current_title = None
            current_packages = []

        # Profile title (indented, not starting with "Packages:")
        elif line and line[0].isspace() and not line.strip().startswith("Packages:"):
            if current_title is None:
                current_title = line.strip()

        # Packages line (indented, starts with "Packages:")
        elif line and line.strip().startswith("Packages:"):
            packages_str = line.strip()[len("Packages:"):].strip()
            if packages_str:
                current_packages = packages_str.split()

    # Save last profile
    if current_profile:
        profiles.append({
            "profile": current_profile,
            "title": current_title or current_profile,
            "packages": current_packages,
        })

    return profiles


def search_profiles(
    target: str,
    subtarget: str,
    query: str,
    version: str = "23.05.2",
) -> List[Dict[str, Any]]:
    """
    Search for profiles matching a query string.

    Args:
        target: OpenWrt target
        subtarget: OpenWrt subtarget
        query: Search query (matches profile name or title)
        version: OpenWrt version

    Returns:
        List of matching profiles
    """
    all_profiles = discover_profiles(target, subtarget, version)

    query_lower = query.lower()
    matching = []

    for profile in all_profiles:
        if (
            query_lower in profile["profile"].lower()
            or query_lower in profile["title"].lower()
        ):
            matching.append(profile)

    return matching


def get_profile_info(
    target: str,
    subtarget: str,
    profile: str,
    version: str = "23.05.2",
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific profile.

    Args:
        target: OpenWrt target
        subtarget: OpenWrt subtarget
        profile: Profile name
        version: OpenWrt version

    Returns:
        Profile information dict or None if not found
    """
    all_profiles = discover_profiles(target, subtarget, version)

    for p in all_profiles:
        if p["profile"] == profile:
            return p

    return None


def get_common_targets() -> List[Dict[str, Any]]:
    """
    Get list of common OpenWrt targets.

    Returns:
        List of common targets with their subtargets
    """
    return [
        {
            "target": "ath79",
            "subtarget": "generic",
            "description": "Atheros AR71xx/AR913x/AR933x (ath79)",
            "manufacturer": "Various (Ubiquiti, TP-Link, etc.)",
        },
        {
            "target": "ath79",
            "subtarget": "nand",
            "description": "Atheros AR71xx/AR913x/AR933x with NAND flash",
            "manufacturer": "Various",
        },
        {
            "target": "ramips",
            "subtarget": "mt7621",
            "description": "MediaTek MT7621 based devices",
            "manufacturer": "Various (Xiaomi, GL.iNet, etc.)",
        },
        {
            "target": "ramips",
            "subtarget": "mt76x8",
            "description": "MediaTek MT76x8 based devices",
            "manufacturer": "Various",
        },
        {
            "target": "ipq40xx",
            "subtarget": "generic",
            "description": "Qualcomm IPQ40xx",
            "manufacturer": "Various (GL.iNet, etc.)",
        },
        {
            "target": "ipq806x",
            "subtarget": "generic",
            "description": "Qualcomm IPQ806x",
            "manufacturer": "Netgear, Linksys",
        },
        {
            "target": "x86",
            "subtarget": "64",
            "description": "x86 64-bit PCs and virtual machines",
            "manufacturer": "Generic x86",
        },
        {
            "target": "bcm27xx",
            "subtarget": "bcm2710",
            "description": "Raspberry Pi 3",
            "manufacturer": "Raspberry Pi Foundation",
        },
        {
            "target": "bcm27xx",
            "subtarget": "bcm2711",
            "description": "Raspberry Pi 4",
            "manufacturer": "Raspberry Pi Foundation",
        },
        {
            "target": "mediatek",
            "subtarget": "mt7622",
            "description": "MediaTek MT7622",
            "manufacturer": "Various",
        },
    ]
