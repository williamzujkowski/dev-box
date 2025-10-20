"""Test VM template generation.

This test suite validates the VMTemplate class following TDD principles.
Tests are written FIRST (RED phase) before implementation.

CRITICAL: NAT-filtered network must be the DEFAULT mode.
"""

import pytest
from typing import Any


class TestVMTemplate:
    """Test VM template generation and XML output."""

    def test_template_generates_valid_xml(self) -> None:
        """Template produces valid libvirt XML structure.

        RED: This test will fail until VMTemplate is implemented.
        GREEN: Implement minimal code to pass.
        REFACTOR: Improve code quality while keeping test green.
        """
        from agent_vm.core.template import VMTemplate, ResourceProfile, NetworkMode

        # Arrange
        template = VMTemplate(
            name="test-vm",
            resources=ResourceProfile(vcpu=2, memory_mib=2048),
            network_mode=NetworkMode.ISOLATED,
        )

        # Act
        xml = template.generate_xml()

        # Assert - Check basic XML structure (flexible quote matching)
        assert '<domain type="kvm">' in xml or "<domain type='kvm'>" in xml
        assert "<name>test-vm</name>" in xml
        assert (
            '<memory unit="MiB">2048</memory>' in xml or "<memory unit='MiB'>2048</memory>" in xml
        )
        assert "<vcpu>2</vcpu>" in xml

    def test_template_includes_security_features(self) -> None:
        """Template includes cgroups resource limits for security."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert - Check for cgroups resource limits
        assert "<cputune>" in xml
        assert "<memtune>" in xml

    def test_template_includes_virtio_devices(self) -> None:
        """Template uses virtio drivers for performance."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert - virtio for disk and network
        assert "virtio" in xml

    def test_template_nat_filtered_network_default(self) -> None:
        """NAT-filtered network is default (CRITICAL REQUIREMENT).

        This is the most important test - agents need internet access by default.
        """
        from agent_vm.core.template import VMTemplate

        # Arrange - Create template WITHOUT specifying network_mode
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert - Must use NAT-filtered network by default
        assert "agent-nat-filtered" in xml
        assert "agent-isolated" not in xml

    def test_template_isolated_network(self) -> None:
        """Isolated network configuration for high security scenarios."""
        from agent_vm.core.template import VMTemplate, NetworkMode

        # Arrange
        template = VMTemplate(name="test-vm", network_mode=NetworkMode.ISOLATED)

        # Act
        xml = template.generate_xml()

        # Assert
        assert "agent-isolated" in xml
        assert "agent-nat-filtered" not in xml

    def test_template_includes_network_filter(self) -> None:
        """Template includes network filter for security.

        Filter should be applied to NAT-filtered and isolated modes.
        """
        from agent_vm.core.template import VMTemplate, NetworkMode

        # Arrange
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert - Network filter reference present
        assert "filterref" in xml
        assert "agent-network-filter" in xml

    def test_template_bridge_network_no_filter(self) -> None:
        """Bridge mode doesn't use network filter (advanced usage)."""
        from agent_vm.core.template import VMTemplate, NetworkMode

        # Arrange
        template = VMTemplate(name="test-vm", network_mode=NetworkMode.BRIDGE)

        # Act
        xml = template.generate_xml()

        # Assert - Bridge network, no filter
        assert "agent-bridge" in xml
        assert "filterref" not in xml

    def test_resource_profile_light(self) -> None:
        """Light resource profile for small workloads."""
        from agent_vm.core.template import VMTemplate, ResourceProfile

        # Arrange
        resources = ResourceProfile(vcpu=1, memory_mib=1024, disk_gib=10)
        template = VMTemplate(name="test-vm", resources=resources)

        # Act
        xml = template.generate_xml()

        # Assert (flexible quote matching)
        assert "<vcpu>1</vcpu>" in xml
        assert (
            '<memory unit="MiB">1024</memory>' in xml or "<memory unit='MiB'>1024</memory>" in xml
        )

    def test_resource_profile_intensive(self) -> None:
        """Intensive resource profile for heavy workloads."""
        from agent_vm.core.template import VMTemplate, ResourceProfile

        # Arrange
        resources = ResourceProfile(vcpu=4, memory_mib=8192, disk_gib=50)
        template = VMTemplate(name="test-vm", resources=resources)

        # Act
        xml = template.generate_xml()

        # Assert (flexible quote matching)
        assert "<vcpu>4</vcpu>" in xml
        assert (
            '<memory unit="MiB">8192</memory>' in xml or "<memory unit='MiB'>8192</memory>" in xml
        )

    def test_template_custom_disk_path(self) -> None:
        """Template accepts custom disk image path."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        custom_path = "/custom/path/disk.qcow2"
        template = VMTemplate(name="test-vm", disk_path=custom_path)

        # Act
        xml = template.generate_xml()

        # Assert
        assert custom_path in xml

    def test_template_default_disk_path(self) -> None:
        """Template generates default disk path from VM name."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        template = VMTemplate(name="my-special-vm")

        # Act
        xml = template.generate_xml()

        # Assert
        assert "/var/lib/libvirt/images/my-special-vm.qcow2" in xml

    def test_network_mode_enum_values(self) -> None:
        """NetworkMode enum has correct values."""
        from agent_vm.core.template import NetworkMode

        # Assert - All three modes exist
        assert NetworkMode.NAT_FILTERED.value == "nat-filtered"
        assert NetworkMode.ISOLATED.value == "isolated"
        assert NetworkMode.BRIDGE.value == "bridge"

    def test_resource_profile_defaults(self) -> None:
        """ResourceProfile has sensible defaults."""
        from agent_vm.core.template import ResourceProfile

        # Arrange & Act
        profile = ResourceProfile()

        # Assert - Standard defaults
        assert profile.vcpu == 2
        assert profile.memory_mib == 2048
        assert profile.disk_gib == 20

    def test_template_includes_cpu_configuration(self) -> None:
        """Template includes CPU configuration for KVM."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert - CPU host-passthrough for performance
        assert "<cpu" in xml
        assert "host-passthrough" in xml

    def test_template_includes_console_devices(self) -> None:
        """Template includes serial console for debugging."""
        from agent_vm.core.template import VMTemplate

        # Arrange
        template = VMTemplate(name="test-vm")

        # Act
        xml = template.generate_xml()

        # Assert
        assert "<serial" in xml or "<console" in xml
