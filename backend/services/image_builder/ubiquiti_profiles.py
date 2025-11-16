"""
Ubiquiti device profiles for OpenWrt firmware building.

This module contains hardware profiles and configurations for Ubiquiti airMAX devices
commonly used in mesh networks.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DeviceProfile:
    """Hardware device profile for firmware building."""

    name: str
    manufacturer: str
    model: str
    openwrt_profile: str
    target: str
    subtarget: str
    flash_size_mb: int
    ram_size_mb: int
    recommended_packages: List[str]
    notes: str


# Ubiquiti NanoStation M Series (2.4GHz and 5GHz)
NANOSTATION_M2 = DeviceProfile(
    name="NanoStation M2",
    manufacturer="Ubiquiti",
    model="NanoStation M2",
    openwrt_profile="ubnt_nanostation-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "ath10k-firmware-qca988x",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="2.4GHz model, good for short-range mesh links"
)

NANOSTATION_M5 = DeviceProfile(
    name="NanoStation M5",
    manufacturer="Ubiquiti",
    model="NanoStation M5",
    openwrt_profile="ubnt_nanostation-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "ath10k-firmware-qca988x",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="5GHz model, recommended for long-range mesh backhaul"
)

# Ubiquiti NanoStation M XW Series (newer hardware)
NANOSTATION_M2_XW = DeviceProfile(
    name="NanoStation M2 XW",
    manufacturer="Ubiquiti",
    model="NanoStation M2 XW",
    openwrt_profile="ubnt_nanostation-m-xw",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=64,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="2.4GHz XW model with more RAM, better performance"
)

NANOSTATION_M5_XW = DeviceProfile(
    name="NanoStation M5 XW",
    manufacturer="Ubiquiti",
    model="NanoStation M5 XW",
    openwrt_profile="ubnt_nanostation-m-xw",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=64,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="5GHz XW model, best for mesh backhaul with 64MB RAM"
)

# Ubiquiti NanoStation Loco M Series
NANOSTATION_LOCO_M2 = DeviceProfile(
    name="NanoStation Loco M2",
    manufacturer="Ubiquiti",
    model="NanoStation Loco M2",
    openwrt_profile="ubnt_nanostation-loco-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Compact 2.4GHz model, good for client access points"
)

NANOSTATION_LOCO_M5 = DeviceProfile(
    name="NanoStation Loco M5",
    manufacturer="Ubiquiti",
    model="NanoStation Loco M5",
    openwrt_profile="ubnt_nanostation-loco-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Compact 5GHz model, short-range mesh links"
)

# Ubiquiti NanoStation Loco M XW Series
NANOSTATION_LOCO_M2_XW = DeviceProfile(
    name="NanoStation Loco M2 XW",
    manufacturer="Ubiquiti",
    model="NanoStation Loco M2 XW",
    openwrt_profile="ubnt_nanostation-loco-m-xw",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=64,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Compact 2.4GHz XW model with 64MB RAM"
)

NANOSTATION_LOCO_M5_XW = DeviceProfile(
    name="NanoStation Loco M5 XW",
    manufacturer="Ubiquiti",
    model="NanoStation Loco M5 XW",
    openwrt_profile="ubnt_nanostation-loco-m-xw",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=64,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Compact 5GHz XW model, better for mesh with 64MB RAM"
)

# Ubiquiti PicoStation M2
PICOSTATION_M2 = DeviceProfile(
    name="PicoStation M2",
    manufacturer="Ubiquiti",
    model="PicoStation M2",
    openwrt_profile="ubnt_picostation-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Ultra-compact 2.4GHz indoor model"
)

# Ubiquiti Bullet M Series
BULLET_M2 = DeviceProfile(
    name="Bullet M2",
    manufacturer="Ubiquiti",
    model="Bullet M2",
    openwrt_profile="ubnt_bullet-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="2.4GHz board with external antenna connector"
)

BULLET_M5 = DeviceProfile(
    name="Bullet M5",
    manufacturer="Ubiquiti",
    model="Bullet M5",
    openwrt_profile="ubnt_bullet-m",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=32,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="5GHz board with external antenna connector"
)

# Ubiquiti UniFi AC Mesh
UNIFI_AC_MESH = DeviceProfile(
    name="UniFi AC Mesh",
    manufacturer="Ubiquiti",
    model="UniFi AC Mesh",
    openwrt_profile="ubnt_unifiac-mesh",
    target="ath79",
    subtarget="generic",
    flash_size_mb=8,
    ram_size_mb=128,
    recommended_packages=[
        "babeld",
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        "-ppp",
        "-ppp-mod-pppoe",
    ],
    notes="Dual-band AC mesh AP with 128MB RAM, excellent for mesh"
)

# Registry of all Ubiquiti devices
UBIQUITI_DEVICES: Dict[str, DeviceProfile] = {
    # NanoStation M series
    "nanostation-m2": NANOSTATION_M2,
    "nanostation-m5": NANOSTATION_M5,
    "nanostation-m2-xw": NANOSTATION_M2_XW,
    "nanostation-m5-xw": NANOSTATION_M5_XW,
    # NanoStation Loco M series
    "nanostation-loco-m2": NANOSTATION_LOCO_M2,
    "nanostation-loco-m5": NANOSTATION_LOCO_M5,
    "nanostation-loco-m2-xw": NANOSTATION_LOCO_M2_XW,
    "nanostation-loco-m5-xw": NANOSTATION_LOCO_M5_XW,
    # Other Ubiquiti devices
    "picostation-m2": PICOSTATION_M2,
    "bullet-m2": BULLET_M2,
    "bullet-m5": BULLET_M5,
    "unifi-ac-mesh": UNIFI_AC_MESH,
}


def get_device_profile(device_key: str) -> Optional[DeviceProfile]:
    """
    Get device profile by key.

    Args:
        device_key: Device key (e.g., "nanostation-m5-xw")

    Returns:
        DeviceProfile if found, None otherwise
    """
    return UBIQUITI_DEVICES.get(device_key.lower())


def list_ubiquiti_devices() -> List[DeviceProfile]:
    """
    Get list of all supported Ubiquiti devices.

    Returns:
        List of DeviceProfile objects
    """
    return list(UBIQUITI_DEVICES.values())


def get_recommended_packages(device_key: str) -> List[str]:
    """
    Get recommended package list for a specific Ubiquiti device.

    Args:
        device_key: Device key

    Returns:
        List of package names (includes packages to add and remove)
    """
    profile = get_device_profile(device_key)
    if profile:
        return profile.recommended_packages
    return []


def get_build_config(device_key: str) -> Optional[Dict[str, any]]:
    """
    Get complete build configuration for a Ubiquiti device.

    Args:
        device_key: Device key

    Returns:
        Build configuration dict or None
    """
    profile = get_device_profile(device_key)
    if not profile:
        return None

    return {
        "name": f"{profile.manufacturer} {profile.model}",
        "openwrt_version": "23.05.2",
        "target": profile.target,
        "subtarget": profile.subtarget,
        "profile": profile.openwrt_profile,
        "base_packages": [p for p in profile.recommended_packages if not p.startswith("-")],
        "removed_packages": [p[1:] for p in profile.recommended_packages if p.startswith("-")],
        "notes": profile.notes,
    }
