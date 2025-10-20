"""VM template generation for libvirt domains.

This module provides dynamic XML generation for KVM domains with:
- NAT-filtered network access by DEFAULT (agents need internet)
- Resource profiles (light, standard, intensive)
- Security features (cgroups, network filtering)
- Performance optimization (virtio devices, host-passthrough CPU)

CRITICAL: NetworkMode.NAT_FILTERED is the DEFAULT to support CLI agents
that require internet access for package managers, APIs, and git operations.
"""

import xml.etree.ElementTree as ET  # nosec B405 - Only used for XML generation, not parsing
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class NetworkMode(Enum):
    """Network isolation modes for VM execution.

    NAT_FILTERED: Default mode - filtered internet access (DNS, HTTP/S, SSH)
    ISOLATED: High security - no network access
    BRIDGE: Advanced - direct host bridge connection
    """

    NAT_FILTERED = "nat-filtered"  # DEFAULT
    ISOLATED = "isolated"
    BRIDGE = "bridge"


@dataclass
class ResourceProfile:
    """VM resource allocation profile.

    Attributes:
        vcpu: Number of virtual CPUs
        memory_mib: Memory allocation in MiB
        disk_gib: Disk size in GiB
    """

    vcpu: int = 2
    memory_mib: int = 2048
    disk_gib: int = 20


class VMTemplate:
    """Generate libvirt domain XML for agent VMs.

    This class generates complete libvirt XML configurations with:
    - KVM virtualization
    - virtio devices for performance
    - cgroups resource limits
    - Network filtering for security
    - Serial console for debugging
    """

    def __init__(
        self,
        name: str,
        resources: ResourceProfile | None = None,
        network_mode: NetworkMode = NetworkMode.NAT_FILTERED,  # DEFAULT
        disk_path: str | None = None,
    ) -> None:
        """Initialize VM template.

        Args:
            name: VM name (used for domain name and default disk path)
            resources: Resource allocation (defaults to standard profile)
            network_mode: Network isolation mode (defaults to NAT_FILTERED)
            disk_path: Path to disk image (defaults to /var/lib/libvirt/images/{name}.qcow2)
        """
        self.name = name
        self.resources = resources or ResourceProfile()
        self.network_mode = network_mode
        self.disk_path = disk_path or f"/var/lib/libvirt/images/{name}.qcow2"
        self._logger = logger.bind(vm_name=name)

    def generate_xml(self) -> str:
        """Generate complete libvirt domain XML.

        Returns:
            XML string for domain definition

        The generated XML includes:
        - KVM domain type with host-passthrough CPU
        - Memory and vCPU configuration
        - cgroups resource limits (CPU and memory)
        - virtio disk with writeback cache
        - virtio network with optional filtering
        - Serial console for debugging
        """
        self._logger.info(
            "generating_vm_xml",
            network_mode=self.network_mode.value,
            vcpu=self.resources.vcpu,
            memory_mib=self.resources.memory_mib,
        )

        # Create root domain element
        domain = ET.Element("domain", type="kvm")

        # Basic configuration
        ET.SubElement(domain, "name").text = self.name
        ET.SubElement(domain, "memory", unit="MiB").text = str(self.resources.memory_mib)
        ET.SubElement(domain, "vcpu").text = str(self.resources.vcpu)

        # OS configuration
        os_elem = ET.SubElement(domain, "os")
        ET.SubElement(os_elem, "type", arch="x86_64").text = "hvm"
        ET.SubElement(os_elem, "boot", dev="hd")

        # CPU configuration (host-passthrough for performance)
        ET.SubElement(domain, "cpu", mode="host-passthrough")

        # Features (ACPI and APIC for hardware compatibility)
        features = ET.SubElement(domain, "features")
        ET.SubElement(features, "acpi")
        ET.SubElement(features, "apic")

        # cgroups CPU resource limits
        cputune = ET.SubElement(domain, "cputune")
        ET.SubElement(cputune, "shares").text = "1024"
        ET.SubElement(cputune, "period").text = "100000"
        ET.SubElement(cputune, "quota").text = str(self.resources.vcpu * 100000)

        # cgroups memory resource limits
        memtune = ET.SubElement(domain, "memtune")
        ET.SubElement(memtune, "hard_limit", unit="MiB").text = str(self.resources.memory_mib)

        # Devices
        devices = ET.SubElement(domain, "devices")

        # virtio disk (high performance)
        self._add_disk_device(devices)

        # virtio network interface with optional filtering
        self._add_network_device(devices)

        # Serial console for debugging
        self._add_console_devices(devices)

        # Convert to string with proper formatting
        xml_str = ET.tostring(domain, encoding="unicode")

        self._logger.info("vm_xml_generated", xml_length=len(xml_str))
        return xml_str

    def _add_disk_device(self, devices: ET.Element) -> None:
        """Add virtio disk device to XML.

        Args:
            devices: Parent devices element
        """
        disk = ET.SubElement(devices, "disk", type="file", device="disk")
        ET.SubElement(disk, "driver", name="qemu", type="qcow2", cache="writeback")
        ET.SubElement(disk, "source", file=self.disk_path)
        ET.SubElement(disk, "target", dev="vda", bus="virtio")

    def _add_network_device(self, devices: ET.Element) -> None:
        """Add virtio network interface with filtering.

        Args:
            devices: Parent devices element
        """
        interface = ET.SubElement(devices, "interface", type="network")

        # Network name based on mode
        network_name = f"agent-{self.network_mode.value}"
        ET.SubElement(interface, "source", network=network_name)

        # virtio for performance
        ET.SubElement(interface, "model", type="virtio")

        # Add network filter (except for bridge mode)
        if self.network_mode != NetworkMode.BRIDGE:
            ET.SubElement(interface, "filterref", filter="agent-network-filter")

    def _add_console_devices(self, devices: ET.Element) -> None:
        """Add serial console devices for debugging.

        Args:
            devices: Parent devices element
        """
        # Serial console
        serial = ET.SubElement(devices, "serial", type="pty")
        ET.SubElement(serial, "target", port="0")

        # Console (compatible with serial)
        console = ET.SubElement(devices, "console", type="pty")
        ET.SubElement(console, "target", type="serial", port="0")
