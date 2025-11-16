"""
Package sets for OpenWrt firmware builds.

Instead of maintaining device-specific profiles, we define package sets
that can be applied to any OpenWrt-supported device.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PackageSet:
    """Package set configuration for firmware builds."""

    name: str
    description: str
    packages: List[str]
    remove_packages: List[str]
    min_flash_mb: int
    min_ram_mb: int
    recommended_for: List[str]


# Minimal mesh package set - Works on low-resource devices
MESH_MINIMAL = PackageSet(
    name="Mesh Minimal",
    description="Minimal mesh routing with Babel - For 4MB+ flash, 32MB+ RAM devices",
    packages=[
        "babeld",
        "kmod-ath9k",
    ],
    remove_packages=[
        "ppp",
        "ppp-mod-pppoe",
        "wpad-basic-mbedtls",  # Remove if space constrained
    ],
    min_flash_mb=4,
    min_ram_mb=32,
    recommended_for=["Low-resource routers", "Legacy hardware"],
)

# Full mesh package set - Recommended for most deployments
MESH_FULL = PackageSet(
    name="Mesh Full",
    description="Complete mesh stack with Babel, WiFi drivers, and basic monitoring",
    packages=[
        # Mesh routing
        "babeld",
        # WiFi drivers
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        # Network utilities
        "ip-full",
        "ethtool",
        # Monitoring
        "collectd",
        "collectd-mod-cpu",
        "collectd-mod-interface",
        "collectd-mod-load",
        "collectd-mod-memory",
    ],
    remove_packages=[
        "ppp",
        "ppp-mod-pppoe",
    ],
    min_flash_mb=8,
    min_ram_mb=64,
    recommended_for=["Modern mesh routers", "XW series devices", "AC devices"],
)

# Gateway package set - For internet gateway nodes
MESH_GATEWAY = PackageSet(
    name="Mesh Gateway",
    description="Mesh node with gateway capabilities (NAT, firewall, QoS)",
    packages=[
        # Mesh routing
        "babeld",
        # WiFi drivers
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        # Gateway features
        "firewall4",
        "nftables",
        "sqm-scripts",
        "luci",
        "luci-app-sqm",
        # Network utilities
        "ip-full",
        "iptables",
        "ethtool",
        # Monitoring
        "collectd",
        "collectd-mod-cpu",
        "collectd-mod-interface",
        "collectd-mod-load",
        "collectd-mod-memory",
    ],
    remove_packages=[],  # Keep PPP for potential WAN connections
    min_flash_mb=16,
    min_ram_mb=128,
    recommended_for=["Gateway routers", "High-RAM devices", "UniFi AC"],
)

# Monitoring package set - Enhanced monitoring and metrics
MESH_MONITORING = PackageSet(
    name="Mesh Monitoring",
    description="Full mesh with enhanced monitoring and metrics collection",
    packages=[
        # Mesh routing
        "babeld",
        # WiFi drivers
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        # Network utilities
        "ip-full",
        "ethtool",
        "tcpdump",
        "iperf3",
        # Enhanced monitoring
        "collectd",
        "collectd-mod-cpu",
        "collectd-mod-interface",
        "collectd-mod-load",
        "collectd-mod-memory",
        "collectd-mod-network",
        "collectd-mod-ping",
        "collectd-mod-wireless",
    ],
    remove_packages=[
        "ppp",
        "ppp-mod-pppoe",
    ],
    min_flash_mb=8,
    min_ram_mb=64,
    recommended_for=["Monitoring nodes", "Testing", "Development"],
)

# Client access point package set
MESH_CLIENT_AP = PackageSet(
    name="Mesh Client AP",
    description="Mesh node optimized for client access (dual SSID, QoS)",
    packages=[
        # Mesh routing
        "babeld",
        # WiFi drivers
        "kmod-ath9k",
        "kmod-ath10k",
        "ath10k-firmware-qca988x-ct",
        # WiFi AP features
        "hostapd-common",
        "wpad-mbedtls",
        # QoS
        "sqm-scripts",
        # Network utilities
        "ip-full",
        "ethtool",
        # Monitoring
        "collectd",
        "collectd-mod-cpu",
        "collectd-mod-interface",
        "collectd-mod-wireless",
    ],
    remove_packages=[
        "ppp",
        "ppp-mod-pppoe",
        "wpad-basic-mbedtls",  # Replaced by wpad-mbedtls
    ],
    min_flash_mb=8,
    min_ram_mb=64,
    recommended_for=["Client access points", "Loco series", "Indoor deployments"],
)


# Registry of all package sets
PACKAGE_SETS: Dict[str, PackageSet] = {
    "mesh-minimal": MESH_MINIMAL,
    "mesh-full": MESH_FULL,
    "mesh-gateway": MESH_GATEWAY,
    "mesh-monitoring": MESH_MONITORING,
    "mesh-client-ap": MESH_CLIENT_AP,
}


def get_package_set(key: str) -> Optional[PackageSet]:
    """
    Get package set by key.

    Args:
        key: Package set key (e.g., "mesh-full")

    Returns:
        PackageSet if found, None otherwise
    """
    return PACKAGE_SETS.get(key.lower())


def list_package_sets() -> List[PackageSet]:
    """
    Get list of all package sets.

    Returns:
        List of PackageSet objects
    """
    return list(PACKAGE_SETS.values())


def get_package_set_for_device(flash_mb: int, ram_mb: int) -> List[str]:
    """
    Get recommended package sets for device hardware specs.

    Args:
        flash_mb: Flash storage size in MB
        ram_mb: RAM size in MB

    Returns:
        List of package set keys that meet hardware requirements
    """
    compatible = []
    for key, pkg_set in PACKAGE_SETS.items():
        if flash_mb >= pkg_set.min_flash_mb and ram_mb >= pkg_set.min_ram_mb:
            compatible.append(key)
    return compatible
