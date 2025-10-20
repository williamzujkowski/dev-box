"""Test project structure and configuration.

This test suite validates that the project follows standard Python package structure
and has required configuration files properly set up.
"""

import pytest
from pathlib import Path


def test_project_structure_exists():
    """Project follows standard Python package structure"""
    root = Path(__file__).parent.parent
    assert (root / "src" / "agent_vm").exists(), "src/agent_vm package missing"
    assert (root / "tests").exists(), "tests directory missing"
    assert (root / "README.md").exists(), "README.md missing"


def test_source_package_structure():
    """Source package has required submodules"""
    root = Path(__file__).parent.parent
    src_dir = root / "src" / "agent_vm"

    # Check main package exists
    assert (src_dir / "__init__.py").exists(), "Package __init__.py missing"
    assert (src_dir / "py.typed").exists(), "PEP 561 marker (py.typed) missing"

    # Check subpackages exist
    required_subpackages = [
        "core",
        "network",
        "storage",
        "security",
        "monitoring",
        "execution",
        "communication",
    ]

    for subpkg in required_subpackages:
        subpkg_path = src_dir / subpkg
        assert subpkg_path.exists(), f"Subpackage {subpkg} missing"
        assert subpkg_path.is_dir(), f"{subpkg} should be a directory"


def test_test_directory_structure():
    """Test directory has proper organization"""
    root = Path(__file__).parent.parent
    tests_dir = root / "tests"

    # Check test subdirectories exist
    assert (tests_dir / "unit").exists(), "tests/unit missing"
    assert (tests_dir / "integration").exists(), "tests/integration missing"
    assert (tests_dir / "e2e").exists(), "tests/e2e missing"


def test_pyproject_configuration():
    """pyproject.toml has required configuration"""
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"

    # This test expects pyproject.toml to exist
    # If not present, it should fail as part of TDD RED phase
    assert pyproject_path.exists(), "pyproject.toml missing (expected for TDD RED phase)"

    # If file exists, verify content
    if pyproject_path.exists():
        import tomli

        config = tomli.loads(pyproject_path.read_text())

        # Check build system
        assert "build-system" in config, "build-system section missing"

        # Check project metadata
        assert "project" in config, "project section missing"
        assert config["project"]["name"] == "agent-vm", "Project name incorrect"
        assert "requires-python" in config["project"], "requires-python missing"

        # Check tool configurations
        assert "tool" in config, "tool section missing"
        # Note: pyproject.toml has [tool.pytest.ini_options] which becomes tool.pytest.ini_options
        tools = config.get("tool", {})
        pytest_config = tools.get("pytest", {})
        assert "ini_options" in pytest_config, "pytest.ini_options config missing"
        assert "mypy" in tools, "mypy config missing"
        assert "black" in tools, "black config missing"
        assert "ruff" in tools, "ruff config missing"


def test_pytest_configuration():
    """pytest configuration is properly set"""
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"

    if not pyproject_path.exists():
        pytest.skip("pyproject.toml not created yet (TDD RED phase)")

    import tomli

    config = tomli.loads(pyproject_path.read_text())
    pytest_config = config.get("tool", {}).get("pytest", {}).get("ini_options", {})

    # Check pytest configuration
    assert "testpaths" in pytest_config, "testpaths not configured"
    assert "tests" in pytest_config["testpaths"], "tests not in testpaths"
    assert "asyncio_mode" in pytest_config, "asyncio_mode not configured"
    assert pytest_config["asyncio_mode"] == "auto", "asyncio_mode should be auto"


def test_mypy_strict_configuration():
    """mypy is configured in strict mode"""
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"

    if not pyproject_path.exists():
        pytest.skip("pyproject.toml not created yet (TDD RED phase)")

    import tomli

    config = tomli.loads(pyproject_path.read_text())
    mypy_config = config.get("tool", {}).get("mypy", {})

    # Check strict mode enabled
    assert mypy_config.get("strict") is True, "mypy strict mode not enabled"
    assert mypy_config.get("python_version") == "3.12", "Python version should be 3.12"


def test_dependencies_defined():
    """Required dependencies are defined"""
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"

    if not pyproject_path.exists():
        pytest.skip("pyproject.toml not created yet (TDD RED phase)")

    import tomli

    config = tomli.loads(pyproject_path.read_text())
    deps = config.get("project", {}).get("dependencies", [])

    # Check critical dependencies
    required_deps = ["libvirt-python", "prometheus-client", "structlog", "pydantic"]

    for dep in required_deps:
        # Check if any dependency starts with the required name
        assert any(d.startswith(dep) for d in deps), f"Required dependency {dep} missing"


def test_dev_dependencies_defined():
    """Development dependencies are defined"""
    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"

    if not pyproject_path.exists():
        pytest.skip("pyproject.toml not created yet (TDD RED phase)")

    import tomli

    config = tomli.loads(pyproject_path.read_text())
    dev_deps = config.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    # Check dev dependencies
    required_dev_deps = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "mypy",
        "black",
        "ruff",
        "bandit",
    ]

    for dep in required_dev_deps:
        assert any(d.startswith(dep) for d in dev_deps), f"Required dev dependency {dep} missing"


def test_guest_directory_exists():
    """Guest directory exists for VM-deployed code"""
    root = Path(__file__).parent.parent
    assert (root / "guest").exists(), "guest directory missing"
    assert (root / "guest").is_dir(), "guest should be a directory"


def test_documentation_files_exist():
    """Core documentation files are present"""
    root = Path(__file__).parent.parent

    required_docs = [
        "README.md",
        "ARCHITECTURE.md",
        "TDD_IMPLEMENTATION_PLAN.md",
        "IMPLEMENTATION_GUIDE.md",
        "GETTING_STARTED.md",
    ]

    for doc in required_docs:
        assert (root / doc).exists(), f"Documentation file {doc} missing"
