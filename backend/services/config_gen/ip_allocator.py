"""
IP address allocation for mesh routers.
Implements MAC-based deterministic IP assignment.
"""

import hashlib
import ipaddress
from typing import Dict


class IPAllocator:
    """
    IP address allocator for mesh routers.

    Implements the MAC-based IP allocation algorithm:
    - Infrastructure: 10.0.0.1 - 10.0.1.254 (508 routers)
    - Client pools: 10.0.2.0 - 10.0.255.255 (126 clients per router)
    """

    def __init__(
        self,
        network_cidr: str = "10.0.0.0/16",
        infrastructure_cidr: str = "10.0.0.0/23",
        client_pool_start: str = "10.0.2.0",
        max_routers: int = 508,
        clients_per_router: int = 126,
    ):
        self.network_cidr = network_cidr
        self.infrastructure_cidr = infrastructure_cidr
        self.client_pool_start = client_pool_start
        self.max_routers = max_routers
        self.clients_per_router = clients_per_router

        # Parse network configuration
        self.network = ipaddress.IPv4Network(network_cidr)
        self.infrastructure = ipaddress.IPv4Network(infrastructure_cidr)

        # Infrastructure range: 10.0.0.1 - 10.0.1.254
        self.router_ip_start = int(self.infrastructure.network_address) + 1
        self.router_ip_end = self.router_ip_start + max_routers - 1

        # Client pool starts at 10.0.2.0
        self.client_pool_base = int(ipaddress.IPv4Address(client_pool_start))

    def allocate_for_mac(self, mac_address: str) -> Dict[str, any]:
        """
        Allocate IP and DHCP pool for a device based on MAC address.

        Args:
            mac_address: MAC address in format AA:BB:CC:DD:EE:FF

        Returns:
            Dict with router_ip, dhcp_start, dhcp_end, subnet_id
        """
        # Hash MAC address to get router index (0-507)
        router_index = self._hash_mac_to_index(mac_address, self.max_routers)

        # Calculate router IP (10.0.0.1 + index)
        router_ip_int = self.router_ip_start + router_index
        router_ip = str(ipaddress.IPv4Address(router_ip_int))

        # Calculate subnet ID for client pool (2-255)
        # We use 254 subnets (2-255), each holding 126 clients
        subnet_id = (router_index % 254) + 2

        # Calculate DHCP pool
        # Each subnet has 256 addresses (.0-.255)
        # We use two pools per subnet to get 126 clients:
        # Pool 1: .1-.126 (126 addresses)
        # Pool 2: .127-.252 (126 addresses)
        # We alternate between pools based on router index

        subnet_base = self.client_pool_base + (subnet_id << 8)  # subnet_id * 256

        if router_index < 254:
            # First 254 routers use pool 1
            dhcp_start_int = subnet_base + 1
            dhcp_end_int = subnet_base + 126
        else:
            # Next 254 routers use pool 2
            dhcp_start_int = subnet_base + 127
            dhcp_end_int = subnet_base + 252

        dhcp_start = str(ipaddress.IPv4Address(dhcp_start_int))
        dhcp_end = str(ipaddress.IPv4Address(dhcp_end_int))

        return {
            "router_ip": router_ip,
            "dhcp_start": dhcp_start,
            "dhcp_end": dhcp_end,
            "subnet_id": subnet_id,
            "router_index": router_index,
        }

    def _hash_mac_to_index(self, mac_address: str, max_value: int) -> int:
        """
        Hash MAC address to deterministic index in range [0, max_value-1].

        Args:
            mac_address: MAC address string
            max_value: Maximum index value

        Returns:
            Index in range [0, max_value-1]
        """
        # Normalize MAC address (remove colons, lowercase)
        mac_normalized = mac_address.replace(":", "").lower()

        # Hash using SHA256
        hash_bytes = hashlib.sha256(mac_normalized.encode()).digest()

        # Convert first 4 bytes to integer
        hash_int = int.from_bytes(hash_bytes[:4], byteorder="big")

        # Map to range [0, max_value-1]
        return hash_int % max_value

    def validate_allocation(self, allocation: Dict[str, any]) -> bool:
        """
        Validate an IP allocation.

        Args:
            allocation: Allocation dict from allocate_for_mac()

        Returns:
            True if allocation is valid
        """
        # Check router IP is in infrastructure range
        router_ip = ipaddress.IPv4Address(allocation["router_ip"])
        if router_ip not in self.infrastructure:
            return False

        # Check DHCP pool is in network range
        dhcp_start = ipaddress.IPv4Address(allocation["dhcp_start"])
        dhcp_end = ipaddress.IPv4Address(allocation["dhcp_end"])

        if dhcp_start not in self.network or dhcp_end not in self.network:
            return False

        # Check pool size is correct (126 addresses)
        pool_size = int(dhcp_end) - int(dhcp_start) + 1
        if pool_size != self.clients_per_router:
            return False

        return True
