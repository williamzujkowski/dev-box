# dev-box

Isolated Ubuntu 24.04 development environments with Vagrant, VirtualBox, and
Libvirt/KVM support.

## 📖 Documentation

For comprehensive documentation, installation guides, and tutorials, visit our
dedicated documentation site:

**🌐 [dev-box Documentation](docs/dev-box-site/)**

The documentation site includes:

- 🚀 **Getting Started** - Installation and setup guides
- 📖 **User Guides** - Daily workflows and best practices
- 🔧 **API Reference** - CLI commands and configuration
- 🔍 **Troubleshooting** - Common issues and solutions

## Quick Start

```bash
# Clone the repository
git clone https://github.com/dev-box/dev-box.git
cd dev-box

# Start your first VM
vagrant up

# SSH into the environment
vagrant ssh

# Create a snapshot
vagrant snapshot push
```

## Key Features

- **🏗️ Isolated Environments** - Clean Ubuntu 24.04 development environments
- **📦 Vagrant & Libvirt** - Built on proven virtualization technologies
- **🔒 Safety First** - Snapshots, rollback capabilities, and resource
  monitoring
- **💻 Developer Friendly** - Pre-configured tools and automated provisioning

## Documentation Structure

This repository maintains documentation in the following locations:

- **`docs/dev-box-site/`** - Main documentation site (Eleventy-based)
- **`CLAUDE.md`** - Claude Code integration and workflow configuration
- **`manifest.md`** - Project structure and file organization

## Development Workflow

For development workflow documentation including Claude Code integration, see
[CLAUDE.md](CLAUDE.md).

## Contributing

Contributions are welcome! Please see the
[documentation site](docs/dev-box-site/) for contributing guidelines and
development setup instructions.

## License

MIT License - see the [documentation site](docs/dev-box-site/) for details.
