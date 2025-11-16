"""
OpenWrt ImageBuilder wrapper.
Builds custom firmware images with embedded configuration.
"""

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.core.config import settings
from backend.services.config_gen.standalone_uci_generator import StandaloneUCIGenerator


class ImageBuilder:
    """
    OpenWrt ImageBuilder wrapper.

    Downloads and uses OpenWrt ImageBuilder to create custom firmware images.
    """

    def __init__(
        self,
        version: str = "23.05.2",
        target: str = "ath79",
        subtarget: str = "generic",
        profile: Optional[str] = None,
    ):
        """
        Initialize ImageBuilder.

        Args:
            version: OpenWrt version (e.g., "23.05.2")
            target: Target architecture (e.g., "ath79", "ramips", "x86")
            subtarget: Target subtarget (e.g., "generic", "nand", "64")
            profile: Device profile (optional, for device-specific builds)
        """
        self.version = version
        self.target = target
        self.subtarget = subtarget
        self.profile = profile or "generic"

        self.base_path = Path(settings.IMAGEBUILDER_PATH)
        self.firmware_path = Path(settings.FIRMWARE_STORAGE_PATH)

        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.firmware_path.mkdir(parents=True, exist_ok=True)

        # Package lists
        self.packages_add: List[str] = []
        self.packages_remove: List[str] = []

        # Files to include
        self.files: Dict[str, str] = {}  # path -> content

        # Build log
        self.log: List[str] = []

    def add_package(self, package: str) -> None:
        """Add a package to the build."""
        if package not in self.packages_add:
            self.packages_add.append(package)

    def remove_package(self, package: str) -> None:
        """Remove a package from the build."""
        if package not in self.packages_remove:
            self.packages_remove.append(package)

    def add_file(self, path: str, content: str) -> None:
        """
        Add a file to be included in the firmware.

        Args:
            path: Absolute path in firmware (e.g., "/etc/uci-defaults/99-config")
            content: File content
        """
        self.files[path] = content

    def embed_autonomous_config(
        self,
        network_cidr: str = "10.0.0.0/16",
        infrastructure_cidr: str = "10.0.0.0/23",
        mesh_ssid: str = "openmesh-backbone",
        mesh_bssid: str = "02:CA:FE:CA:CA:40",
        client_ssid: Optional[str] = None,
        client_password: Optional[str] = None,
        client_encryption: str = "psk2",
        platform_url: str = "http://10.0.0.1:8000",
    ) -> None:
        """
        Embed standalone autonomous configuration in firmware.

        Generates and embeds the UCI defaults script that enables routers to:
        - Calculate their IP address locally from MAC (no server needed)
        - Configure network, Babel, WiFi autonomously
        - Join mesh network automatically
        - Report to platform for monitoring (optional)

        Args:
            network_cidr: Network CIDR (default: 10.0.0.0/16)
            infrastructure_cidr: Infrastructure CIDR for Babel (default: 10.0.0.0/23)
            mesh_ssid: Mesh ad-hoc SSID
            mesh_bssid: Mesh BSSID (must be same for all nodes)
            client_ssid: Optional client AP SSID
            client_password: Optional client AP password
            client_encryption: Client AP encryption type
            platform_url: Platform URL for heartbeat (default: http://10.0.0.1:8000)
        """
        # Generate standalone UCI configuration script
        generator = StandaloneUCIGenerator(
            network_cidr=network_cidr,
            infrastructure_cidr=infrastructure_cidr,
            mesh_ssid=mesh_ssid,
            mesh_bssid=mesh_bssid,
            client_ssid=client_ssid,
            client_password=client_password,
            client_encryption=client_encryption,
            platform_url=platform_url,
        )

        uci_script = generator.generate()

        # Add UCI defaults script (will run on first boot)
        self.add_file("/etc/uci-defaults/99-openmesh-config", uci_script)

        # Add heartbeat script
        heartbeat_script = self._get_heartbeat_script(platform_url)
        self.add_file("/usr/bin/openmesh-heartbeat.sh", heartbeat_script)

        # Add cron job for heartbeat (runs every minute)
        cron_entry = "* * * * * /usr/bin/openmesh-heartbeat.sh\n"
        self.add_file("/etc/crontabs/root", cron_entry)

        self.log.append("Embedded autonomous mesh configuration")

    def _get_heartbeat_script(self, platform_url: str) -> str:
        """
        Get the heartbeat script content.

        Args:
            platform_url: Platform URL for heartbeat

        Returns:
            Heartbeat script content
        """
        # Read the heartbeat script from node-scripts directory
        # For now, we'll embed it inline
        heartbeat_script = """#!/bin/sh
#
# OpenMesh Heartbeat and Metrics Collection Script
#
# Configuration
PLATFORM_URL="${OPENMESH_PLATFORM_URL:-""" + platform_url + """}"
TIMEOUT=10

# Get device information
get_device_info() {
    MAC=$(cat /sys/class/net/br-lan/address 2>/dev/null || cat /sys/class/net/eth0/address 2>/dev/null)
    IP=$(uci get network.lan.ipaddr 2>/dev/null)
    HOSTNAME=$(uci get system.@system[0].hostname 2>/dev/null || hostname)
    echo "$MAC|$IP|$HOSTNAME"
}

# Collect system metrics
get_system_metrics() {
    CPU_USAGE=$(top -bn1 | grep '^CPU:' | awk '{gsub("%",""); print $2}')
    [ -z "$CPU_USAGE" ] && CPU_USAGE=0
    MEM_TOTAL=$(free | grep '^Mem:' | awk '{print int($2/1024)}')
    MEM_FREE=$(free | grep '^Mem:' | awk '{print int($4/1024)}')
    LOAD_AVG=$(cat /proc/loadavg | awk '{print $1","$2","$3}')
    UPTIME=$(cat /proc/uptime | awk '{print int($1)}')
    FIRMWARE=$(cat /etc/openwrt_release | grep DISTRIB_DESCRIPTION | cut -d"'" -f2)
    echo "$CPU_USAGE|$MEM_TOTAL|$MEM_FREE|$LOAD_AVG|$UPTIME|$FIRMWARE"
}

# Collect Babel metrics
get_babel_metrics() {
    if ! pgrep -x babeld > /dev/null; then
        echo "0|0|0|0|0"
        return
    fi
    BABEL_DUMP=$(echo "dump" | nc -w 2 localhost 33123 2>/dev/null)
    [ -z "$BABEL_DUMP" ] && echo "0|0|0|0|0" && return
    NEIGHBOR_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add neighbour ")
    ROUTE_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add route ")
    INSTALLED_COUNT=$(echo "$BABEL_DUMP" | grep "^add route " | grep -c "installed yes")
    XROUTE_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add xroute ")
    AVG_RTT=0
    echo "$NEIGHBOR_COUNT|$ROUTE_COUNT|$INSTALLED_COUNT|$XROUTE_COUNT|$AVG_RTT"
}

# Send heartbeat
send_heartbeat() {
    local mac=$1 ip=$2 hostname=$3 cpu=$4 mem_total=$5 mem_free=$6 load_avg=$7 uptime=$8 firmware=$9
    shift 9
    local neighbors=$1 routes=$2 installed=$3 xroutes=$4 avg_rtt=$5

    JSON_PAYLOAD=$(cat <<EOF
{
    "mac_address": "$mac",
    "ip_address": "$ip",
    "hostname": "$hostname",
    "cpu_usage_percent": $cpu,
    "memory_total_mb": $mem_total,
    "memory_free_mb": $mem_free,
    "load_average": "$load_avg",
    "uptime_seconds": $uptime,
    "firmware_version": "$firmware",
    "neighbor_count": $neighbors,
    "route_count": $routes
}
EOF
)
    curl -s -m $TIMEOUT -X POST -H "Content-Type: application/json" -d "$JSON_PAYLOAD" "${PLATFORM_URL}/api/v1/devices/heartbeat" >/dev/null 2>&1 || true
}

# Main
DEVICE_INFO=$(get_device_info)
[ $? -ne 0 ] && exit 1
MAC=$(echo "$DEVICE_INFO" | cut -d'|' -f1)
IP=$(echo "$DEVICE_INFO" | cut -d'|' -f2)
HOSTNAME=$(echo "$DEVICE_INFO" | cut -d'|' -f3)
SYSTEM_METRICS=$(get_system_metrics)
BABEL_METRICS=$(get_babel_metrics)
send_heartbeat "$MAC" "$IP" "$HOSTNAME" \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f1) \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f2) \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f3) \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f4) \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f5) \
    $(echo "$SYSTEM_METRICS" | cut -d'|' -f6) \
    $(echo "$BABEL_METRICS" | cut -d'|' -f1) \
    $(echo "$BABEL_METRICS" | cut -d'|' -f2) \
    $(echo "$BABEL_METRICS" | cut -d'|' -f3) \
    $(echo "$BABEL_METRICS" | cut -d'|' -f4) \
    $(echo "$BABEL_METRICS" | cut -d'|' -f5)
"""
        return heartbeat_script

    def _download_imagebuilder(self) -> Path:
        """
        Download OpenWrt ImageBuilder if not present.

        Returns:
            Path to ImageBuilder directory
        """
        # ImageBuilder naming: openwrt-imagebuilder-{version}-{target}-{subtarget}.Linux-x86_64
        ib_name = f"openwrt-imagebuilder-{self.version}-{self.target}-{self.subtarget}.Linux-x86_64"
        ib_dir = self.base_path / ib_name
        ib_archive = self.base_path / f"{ib_name}.tar.xz"

        # Check if already exists
        if ib_dir.exists():
            self.log.append(f"ImageBuilder found: {ib_dir}")
            return ib_dir

        # Download URL
        download_url = (
            f"https://downloads.openwrt.org/releases/{self.version}/targets/"
            f"{self.target}/{self.subtarget}/{ib_name}.tar.xz"
        )

        self.log.append(f"Downloading ImageBuilder from {download_url}")

        try:
            # Download
            subprocess.run(
                ["wget", "-O", str(ib_archive), download_url],
                check=True,
                capture_output=True,
                text=True,
            )

            # Extract
            self.log.append(f"Extracting ImageBuilder to {self.base_path}")
            subprocess.run(
                ["tar", "-xJf", str(ib_archive), "-C", str(self.base_path)],
                check=True,
                capture_output=True,
                text=True,
            )

            # Cleanup archive
            ib_archive.unlink()

            self.log.append(f"ImageBuilder ready: {ib_dir}")
            return ib_dir

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to download ImageBuilder: {e.stderr}"
            self.log.append(error_msg)
            raise RuntimeError(error_msg)

    def _prepare_files_dir(self) -> Optional[Path]:
        """
        Prepare files directory for inclusion in firmware.

        Returns:
            Path to files directory, or None if no files
        """
        if not self.files:
            return None

        # Create temporary files directory
        files_dir = tempfile.mkdtemp(prefix="openmesh-files-")
        files_path = Path(files_dir)

        for file_path, content in self.files.items():
            # Remove leading slash
            rel_path = file_path.lstrip("/")
            target_path = files_path / rel_path

            # Create parent directories
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            target_path.write_text(content)

            # Make scripts executable
            if "uci-defaults" in file_path or file_path.endswith(".sh"):
                target_path.chmod(0o755)

        self.log.append(f"Prepared files directory: {files_path}")
        return files_path

    def build(self) -> Dict[str, Any]:
        """
        Build the firmware image.

        Returns:
            dict: Build result with success status and image details
        """
        try:
            # Download ImageBuilder if needed
            ib_dir = self._download_imagebuilder()

            # Prepare files
            files_dir = self._prepare_files_dir()

            # Build package list
            packages = " ".join(self.packages_add)
            if self.packages_remove:
                packages += " " + " ".join([f"-{pkg}" for pkg in self.packages_remove])

            # Build command
            make_cmd = [
                "make",
                "image",
                f"PROFILE={self.profile}",
            ]

            if packages:
                make_cmd.append(f"PACKAGES={packages}")

            if files_dir:
                make_cmd.append(f"FILES={files_dir}")

            self.log.append(f"Building image with command: {' '.join(make_cmd)}")

            # Run build
            result = subprocess.run(
                make_cmd,
                cwd=ib_dir,
                capture_output=True,
                text=True,
                timeout=settings.BUILD_TIMEOUT_SECONDS,
            )

            self.log.append(result.stdout)

            if result.returncode != 0:
                self.log.append(f"Build failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "log": "\n".join(self.log),
                }

            # Find built image
            bin_dir = ib_dir / "bin" / "targets" / self.target / self.subtarget
            image_files = list(bin_dir.glob("openwrt-*.bin"))

            if not image_files:
                # Try .img extension
                image_files = list(bin_dir.glob("openwrt-*.img"))

            if not image_files:
                error = "No firmware image found after build"
                self.log.append(error)
                return {"success": False, "error": error, "log": "\n".join(self.log)}

            # Use first image file (or we can be more selective)
            source_image = image_files[0]

            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            dest_filename = f"openmesh-{self.version}-{self.target}-{self.subtarget}-{timestamp}.bin"
            dest_path = self.firmware_path / dest_filename

            # Copy image to firmware storage
            import shutil

            shutil.copy2(source_image, dest_path)

            # Calculate checksum
            checksum = self._calculate_checksum(dest_path)

            # Get file size
            file_size = dest_path.stat().st_size

            self.log.append(f"Build successful: {dest_path}")
            self.log.append(f"Size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            self.log.append(f"SHA256: {checksum}")

            # Cleanup files directory
            if files_dir:
                shutil.rmtree(files_dir)

            return {
                "success": True,
                "image_filename": dest_filename,
                "image_path": str(dest_path),
                "image_size": file_size,
                "checksum": checksum,
                "log": "\n".join(self.log),
            }

        except subprocess.TimeoutExpired:
            error = f"Build timeout after {settings.BUILD_TIMEOUT_SECONDS} seconds"
            self.log.append(error)
            return {"success": False, "error": error, "log": "\n".join(self.log)}

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            self.log.append(error)
            return {"success": False, "error": error, "log": "\n".join(self.log)}

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def get_default_packages() -> List[str]:
    """
    Get default package list for OpenMesh firmware.

    Returns:
        List of package names
    """
    return [
        # Core system
        "base-files",
        "busybox",
        "libc",
        "libgcc",
        "ca-bundle",
        # Networking
        "dnsmasq",
        "firewall4",
        "ip-full",
        "ipset",
        "nftables",
        "odhcp6c",
        "odhcpd-ipv6only",
        # Routing - Babel
        "babeld",
        # WiFi
        "hostapd-common",
        "iw",
        "wpad-basic-mbedtls",
        # Utilities
        "curl",
        "htop",
        "tcpdump",
        "ethtool",
        # Monitoring
        "collectd",
        "collectd-mod-cpu",
        "collectd-mod-interface",
        "collectd-mod-load",
        "collectd-mod-memory",
        "collectd-mod-network",
    ]
