"""
Standalone UCI configuration script generator for OpenWrt mesh routers.
Generates self-contained scripts that calculate IP addresses locally without server dependency.
Based on the comprehensive mesh network plan.
"""

from typing import Optional


class StandaloneUCIGenerator:
    """
    Generates standalone UCI configuration scripts for autonomous mesh formation.

    The generated script:
    - Calculates router IP from MAC address using SHA256 hash (local calculation)
    - Calculates DHCP pool from MAC address using MD5 hash
    - Configures network, Babel, WiFi autonomously
    - Requires NO server connectivity to function
    - Optionally reports to platform for monitoring
    """

    def __init__(
        self,
        network_cidr: str = "10.0.0.0/16",
        infrastructure_cidr: str = "10.0.0.0/23",
        max_routers: int = 508,
        clients_per_router: int = 126,
        mesh_ssid: str = "mesh-backbone",
        mesh_bssid: str = "02:CA:FE:CA:CA:40",
        mesh_password: Optional[str] = None,
        client_ssid: Optional[str] = None,
        client_password: Optional[str] = None,
        client_encryption: str = "psk2",
        platform_url: Optional[str] = None,
    ):
        self.network_cidr = network_cidr
        self.infrastructure_cidr = infrastructure_cidr
        self.max_routers = max_routers
        self.clients_per_router = clients_per_router
        self.mesh_ssid = mesh_ssid
        self.mesh_bssid = mesh_bssid
        self.mesh_password = mesh_password
        self.client_ssid = client_ssid
        self.client_password = client_password
        self.client_encryption = client_encryption
        self.platform_url = platform_url or "http://10.0.0.1:8000"

    def generate(self) -> str:
        """
        Generate complete standalone UCI defaults script.

        Returns:
            Shell script content for /etc/uci-defaults/99-openmesh-config
        """
        script = f"""#!/bin/sh
# OpenMesh Auto-Configuration Script
# This script is STANDALONE - requires NO server connectivity
#
# Network: {self.network_cidr}
# Infrastructure: {self.infrastructure_cidr}
# Max Routers: {self.max_routers}
# Clients per Router: {self.clients_per_router}
# Mesh SSID: {self.mesh_ssid}

set -e

echo "=============================================="
echo "OpenMesh: Starting auto-configuration..."
echo "=============================================="

#
# Helper Functions
#

# Get MAC address from various sources (priority order)
get_mac_from_uci() {{
    # Option 1: WiFi MAC from first radio (preferred)
    MAC=$(uci get wireless.@wifi-device[0].macaddr 2>/dev/null)

    # Option 2: System board MAC
    if [ -z "$MAC" ]; then
        MAC=$(uci get system.@system[0].macaddr 2>/dev/null)
    fi

    # Option 3: LAN interface MAC
    if [ -z "$MAC" ]; then
        LAN_IFACE=$(uci get network.lan.ifname 2>/dev/null)
        if [ -n "$LAN_IFACE" ] && [ -f "/sys/class/net/$LAN_IFACE/address" ]; then
            MAC=$(cat /sys/class/net/$LAN_IFACE/address)
        fi
    fi

    # Option 4: br-lan bridge MAC
    if [ -z "$MAC" ]; then
        MAC=$(cat /sys/class/net/br-lan/address 2>/dev/null)
    fi

    # Option 5: eth0 fallback
    if [ -z "$MAC" ]; then
        MAC=$(cat /sys/class/net/eth0/address 2>/dev/null)
    fi

    # Option 6: First non-loopback interface
    if [ -z "$MAC" ]; then
        for iface in /sys/class/net/*; do
            iface_name=$(basename "$iface")
            if [ "$iface_name" != "lo" ]; then
                MAC=$(cat "$iface/address" 2>/dev/null)
                if [ -n "$MAC" ]; then
                    break
                fi
            fi
        done
    fi

    echo "$MAC"
}}

# Generate router infrastructure IP from MAC using SHA256 hash
generate_router_ip() {{
    local mac=$1
    local hash=$(echo -n "$mac" | sha256sum | cut -c1-8)
    local decimal=$((0x$hash))
    local host_offset=$(($decimal % {self.max_routers} + 1))

    local third_octet=$(($host_offset / 256))
    local fourth_octet=$(($host_offset % 256))

    # Boundary protection: keep within 10.0.0.1 - 10.0.1.254
    if [ $third_octet -gt 1 ]; then
        third_octet=1
        fourth_octet=254
    fi
    if [ $fourth_octet -eq 0 ]; then
        fourth_octet=1
    fi
    if [ $fourth_octet -eq 255 ]; then
        fourth_octet=254
    fi

    echo "10.0.$third_octet.$fourth_octet"
}}

# Generate router sequence for DHCP pool assignment
generate_router_sequence() {{
    local mac=$1
    local hash=$(echo -n "$mac" | md5sum | cut -c1-6)
    local decimal=$((0x$hash))
    local sequence=$(($decimal % {self.max_routers} + 1))
    echo $sequence
}}

# Calculate DHCP pool start IP in client zone
calculate_dhcp_pool() {{
    local router_sequence=$1
    local subnet_offset=$((($router_sequence - 1) / 2))
    local pool_in_subnet=$((($router_sequence - 1) % 2))

    local third_octet=$((2 + $subnet_offset))
    if [ $third_octet -gt 255 ]; then
        third_octet=$((2 + ($subnet_offset % 254)))
    fi

    if [ $pool_in_subnet -eq 0 ]; then
        fourth_octet=1      # First pool: .1-.126
    else
        fourth_octet=127    # Second pool: .127-.252
    fi

    echo "10.0.$third_octet.$fourth_octet"
}}

#
# Step 1: Generate Configuration Values
#
echo "OpenMesh: Generating configuration from MAC address..."

MAC=$(get_mac_from_uci)
if [ -z "$MAC" ]; then
    echo "ERROR: Could not determine MAC address"
    exit 1
fi

HOSTNAME="mesh-$(echo $MAC | tail -c 9 | tr -d ':' | tr 'a-f' 'A-F')"
ROUTER_IP=$(generate_router_ip "$MAC")
ROUTER_SEQ=$(generate_router_sequence "$MAC")
DHCP_START_IP=$(calculate_dhcp_pool "$ROUTER_SEQ")
DHCP_START_4TH=$(echo $DHCP_START_IP | cut -d. -f4)

echo "  MAC Address: $MAC"
echo "  Hostname: $HOSTNAME"
echo "  Router IP: $ROUTER_IP"
echo "  DHCP Pool Start: $DHCP_START_IP"
echo "  DHCP Clients: {self.clients_per_router}"

#
# Step 2: Configure Network
#
echo "OpenMesh: Configuring network interface..."

uci set network.lan.proto='static'
uci set network.lan.ipaddr="$ROUTER_IP"
uci set network.lan.netmask='255.255.0.0'
uci set network.lan.ip6assign=''

#
# Step 3: Configure DHCP Server
#
echo "OpenMesh: Configuring DHCP server..."

uci set dhcp.lan.start="$DHCP_START_4TH"
uci set dhcp.lan.limit='{self.clients_per_router}'
uci set dhcp.lan.leasetime='12h'
uci set dhcp.lan.ignore='0'

#
# Step 4: Configure Hostname
#
echo "OpenMesh: Setting hostname..."

uci set system.@system[0].hostname="$HOSTNAME"

#
# Step 5: Install and Configure Babel Routing
#
echo "OpenMesh: Configuring Babel routing protocol..."

# Check if babeld is installed
if ! opkg list-installed | grep -q '^babeld '; then
    echo "OpenMesh: Installing babeld..."
    opkg update
    opkg install babeld
fi

# Configure Babel general settings
uci set babeld.general=general
uci set babeld.general.ipv6_subtrees='true'
uci set babeld.general.export_table='254'
uci set babeld.general.import_table='254'
uci set babeld.general.local_server='33123'

# Configure Babel on LAN interface (wired)
uci set babeld.lan=interface
uci set babeld.lan.ifname='br-lan'
uci set babeld.lan.type='wired'

# Add mesh WiFi interface to Babel (will be configured later)
uci set babeld.mesh_wifi=interface
uci set babeld.mesh_wifi.ifname='wlan0-1'
uci set babeld.mesh_wifi.type='wireless'
uci set babeld.mesh_wifi.rxcost='256'

# CRITICAL: Only redistribute infrastructure routes (10.0.0.0/23)
# This prevents redistributing 64K client routes!
uci set babeld.infra_routes=filter
uci set babeld.infra_routes.type='redistribute'
uci set babeld.infra_routes.ip='{self.infrastructure_cidr}'
uci set babeld.infra_routes.action='allow'

# Redistribute default routes from DHCP
uci set babeld.default_route=filter
uci set babeld.default_route.type='redistribute'
uci set babeld.default_route.ip='0.0.0.0/0'
uci set babeld.default_route.eq='0'
uci set babeld.default_route.proto='3'
uci set babeld.default_route.action='metric 128'

# Block everything else from redistribution
uci set babeld.deny_rest=filter
uci set babeld.deny_rest.type='redistribute'
uci set babeld.deny_rest.action='deny'

#
# Step 6: Configure WiFi Mesh
#
echo "OpenMesh: Configuring mesh WiFi..."

# Get first WiFi radio
RADIO=$(uci show wireless | grep 'wifi-device' | head -n 1 | cut -d. -f2 | cut -d= -f1)

if [ -n "$RADIO" ]; then
    # Enable radio and set basic parameters
    uci set wireless.${{RADIO}}.disabled='0'
    uci set wireless.${{RADIO}}.country='US'
    uci set wireless.${{RADIO}}.channel='auto'

    # Delete any existing mesh interface
    uci delete wireless.mesh 2>/dev/null || true

    # Create mesh ad-hoc interface
    uci set wireless.mesh=wifi-iface
    uci set wireless.mesh.device="$RADIO"
    uci set wireless.mesh.mode='adhoc'
    uci set wireless.mesh.ssid='{self.mesh_ssid}'
    uci set wireless.mesh.network='lan'
    uci set wireless.mesh.encryption='none'
    uci set wireless.mesh.bssid='{self.mesh_bssid}'
    uci set wireless.mesh.mcast_rate='24000'

    echo "  Mesh interface configured on radio: $RADIO"
"""

        # Add client AP if configured
        if self.client_ssid:
            script += f"""
    # Delete any existing client AP interface
    uci delete wireless.client_ap 2>/dev/null || true

    # Create client AP interface
    uci set wireless.client_ap=wifi-iface
    uci set wireless.client_ap.device="$RADIO"
    uci set wireless.client_ap.mode='ap'
    uci set wireless.client_ap.ssid='{self.client_ssid}'
    uci set wireless.client_ap.network='lan'
    uci set wireless.client_ap.encryption='{self.client_encryption}'
"""
            if self.client_encryption != 'none' and self.client_password:
                script += f"    uci set wireless.client_ap.key='{self.client_password}'\n"

            script += """
    echo "  Client AP configured: {self.client_ssid}"
"""

        script += """
else
    echo "  WARNING: No WiFi radio found, skipping mesh WiFi setup"
fi

#
# Step 7: Configure Firewall
#
echo "OpenMesh: Configuring firewall rules..."

# Allow Babel routing protocol (UDP port 6696)
uci set firewall.babel=rule
uci set firewall.babel.name='Allow-Babel'
uci set firewall.babel.src='*'
uci set firewall.babel.proto='udp'
uci set firewall.babel.dest_port='6696'
uci set firewall.babel.target='ACCEPT'

# Allow Babel local control server (TCP port 33123)
uci set firewall.babel_local=rule
uci set firewall.babel_local.name='Allow-Babel-Local'
uci set firewall.babel_local.src='lan'
uci set firewall.babel_local.proto='tcp'
uci set firewall.babel_local.dest_port='33123'
uci set firewall.babel_local.target='ACCEPT'

#
# Step 8: Commit All Changes
#
echo "OpenMesh: Committing configuration..."

uci commit network
uci commit dhcp
uci commit system
uci commit babeld
uci commit wireless
uci commit firewall

#
# Step 9: Restart Services
#
echo "OpenMesh: Restarting services..."

/etc/init.d/network restart
sleep 3
/etc/init.d/dnsmasq restart
/etc/init.d/babeld enable
/etc/init.d/babeld start
/etc/init.d/firewall restart

# Restart WiFi (delayed to ensure network is up)
sleep 2
wifi

#
# Step 10: Log Configuration
#
logger "OpenMesh auto-config: IP=$ROUTER_IP, DHCP=$DHCP_START_IP, Hostname=$HOSTNAME"

echo ""
echo "=============================================="
echo "OpenMesh: Configuration Complete!"
echo "=============================================="
echo "  Router IP: $ROUTER_IP"
echo "  DHCP Pool: $DHCP_START_IP - $(echo $DHCP_START_IP | cut -d. -f1-3).$(($DHCP_START_4TH + {self.clients_per_router} - 1))"
echo "  Hostname: $HOSTNAME"
echo "  Mesh SSID: {self.mesh_ssid}"
"""

        if self.client_ssid:
            script += f"""echo "  Client SSID: {self.client_ssid}"
"""

        script += """
echo "=============================================="
echo ""

#
# Step 11: Optional Platform Registration
#
echo "OpenMesh: Attempting platform registration..."
echo "  Platform URL: """ + self.platform_url + """"

# Try to register with platform (non-blocking, fire-and-forget)
# Router will function normally even if platform is unreachable
(
    RESPONSE=$(curl -s -m 10 -w "\\n%{{http_code}}" \\
        -X POST \\
        -H "Content-Type: application/json" \\
        -d "{\\"mac_address\\":\\"$MAC\\",\\"ip_address\\":\\"$ROUTER_IP\\",\\"hostname\\":\\"$HOSTNAME\\"}" \\
        "{self.platform_url}/api/v1/devices/heartbeat" 2>/dev/null || echo "000")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        echo "  Platform registration successful!"
        logger "OpenMesh: Registered with platform at {self.platform_url}"
    else
        echo "  Platform unreachable (will retry via cron)"
        logger "OpenMesh: Platform unreachable at {self.platform_url}, will retry"
    fi
) &

# Remove this script after execution
rm /etc/uci-defaults/99-openmesh-config

echo "OpenMesh: Router is now part of the mesh network!"
exit 0
"""

        return script

    def generate_to_file(self, output_path: str) -> None:
        """
        Generate script and write to file.

        Args:
            output_path: Path to write script to
        """
        script = self.generate()
        with open(output_path, 'w') as f:
            f.write(script)
