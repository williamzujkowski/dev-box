---
layout: page.njk
title: "User Guides"
description:
  "Comprehensive guides covering all aspects of the dev-box development
  environment platform"
eleventyNavigation:
  key: Guides
  order: 2
---

# User Guides

Comprehensive documentation covering all aspects of using and customizing your
dev-box development environments.

## Getting Started Guides

### [Installation & Setup](/getting-started/)

Complete walkthrough for installing prerequisites, setting up your first VM, and
basic configuration.

### [First Steps](/guides/first-steps/)

Essential workflows and commands to get productive with your new development
environment.

## Core Workflows

### [Vagrant Workflow](/guides/vagrant-workflow/)

Master the essential Vagrant commands and workflows for daily development tasks.

**Topics covered:**

- VM lifecycle management
- SSH access and file sharing
- Port forwarding and networking
- Snapshot management
- Multi-VM environments

### [Provisioning & Customization](/guides/provisioning/)

Learn how to customize your development environment with additional tools and
configurations.

**Topics covered:**

- Custom provisioning scripts
- Installing additional software
- Environment configuration
- Dotfiles integration
- Development toolchain setup

## Advanced Configuration

### [Libvirt/KVM Setup](/guides/libvirt-setup/)

Switch from VirtualBox to Libvirt/KVM for better performance on Linux systems.

**Topics covered:**

- Libvirt installation and configuration
- KVM module management
- Performance optimization
- Troubleshooting KVM issues
- Migration from VirtualBox

### [Network Configuration](/guides/networking/)

Advanced networking setups for complex development scenarios.

**Topics covered:**

- Custom network topologies
- Multi-VM communication
- Bridge networking
- VPN integration
- Security considerations

## Development Environments

### [Node.js Development](/guides/nodejs-development/)

Optimize your dev-box environment for Node.js and JavaScript development.

**Topics covered:**

- Node.js version management (nvm)
- npm and yarn configuration
- Popular framework setups
- Database integration
- Testing environments

### [Python Development](/guides/python-development/)

Configure Python development environments with virtual environments and common
tools.

**Topics covered:**

- Python version management (pyenv)
- Virtual environment best practices
- Package management with pip
- Django and Flask setups
- Data science toolkits

### [Docker Development](/guides/docker-development/)

Leverage Docker within your dev-box environment for containerized development.

**Topics covered:**

- Docker and docker-compose setup
- Container development workflows
- Volume management
- Registry integration
- Kubernetes development

## Safety & Recovery

### [Snapshot Management](/guides/snapshots/)

Master VM snapshots for safe experimentation and quick recovery.

**Topics covered:**

- Creating and managing snapshots
- Snapshot strategies
- Automated snapshot scripts
- Recovery procedures
- Best practices

### [Backup & Recovery](/guides/backup-recovery/)

Comprehensive backup strategies to protect your development work.

**Topics covered:**

- VM backup procedures
- Data synchronization
- Disaster recovery planning
- Migration between hosts
- Cloud backup integration

## Performance & Optimization

### [Performance Tuning](/guides/performance/)

Optimize your dev-box environment for maximum performance.

**Topics covered:**

- Resource allocation tuning
- Storage optimization
- Network performance
- Host system optimization
- Monitoring and profiling

### [Resource Management](/guides/resources/)

Monitor and manage system resources effectively.

**Topics covered:**

- CPU and memory monitoring
- Disk usage optimization
- Network bandwidth management
- Resource limits and quotas
- Performance troubleshooting

## Team Collaboration

### [Team Workflows](/guides/team-workflows/)

Best practices for using dev-box in team environments.

**Topics covered:**

- Shared Vagrantfile management
- Environment standardization
- Version control integration
- Team onboarding
- Collaboration tools

### [CI/CD Integration](/guides/cicd/)

Integrate dev-box environments with continuous integration and deployment
pipelines.

**Topics covered:**

- GitHub Actions integration
- GitLab CI setup
- Jenkins configuration
- Automated testing
- Deployment strategies

## Security

### [Security Best Practices](/guides/security/)

Secure your development environments and protect sensitive data.

**Topics covered:**

- VM security hardening
- Network security
- Credential management
- Access controls
- Security monitoring

### [Isolation Strategies](/guides/isolation/)

Maintain proper isolation between development environments and your host system.

**Topics covered:**

- Sandbox principles
- Network isolation
- File system security
- Process isolation
- Risk mitigation

## Troubleshooting Guides

### [Common Issues](/troubleshooting/common-issues/)

Solutions to frequently encountered problems and error messages.

### [Performance Issues](/troubleshooting/performance/)

Diagnose and resolve performance problems in your development environment.

### [Network Problems](/troubleshooting/networking/)

Fix connectivity, port forwarding, and network configuration issues.

### [Recovery Procedures](/troubleshooting/recovery/)

Step-by-step recovery procedures for various failure scenarios.

## Advanced Topics

### [Custom Box Creation](/guides/custom-boxes/)

Create your own custom Vagrant boxes for specialized development needs.

**Topics covered:**

- Box building process
- Custom base images
- Box distribution
- Version management
- Automated builds

### [Plugin Development](/guides/plugins/)

Extend dev-box functionality with custom scripts and integrations.

**Topics covered:**

- Hook system usage
- Custom provisioning scripts
- Integration development
- Plugin architecture
- Testing and debugging

### [Automation Scripts](/guides/automation/)

Automate common tasks and workflows with custom scripts.

**Topics covered:**

- Shell script integration
- Task automation
- Monitoring scripts
- Deployment automation
- Maintenance tasks

## Migration Guides

### [From Other Platforms](/guides/migration/)

Migrate existing development environments to dev-box.

**Topics covered:**

- Docker Desktop migration
- WSL2 migration
- Native development migration
- Data migration strategies
- Tool compatibility

### [Between Providers](/guides/provider-migration/)

Switch between VirtualBox and Libvirt providers.

**Topics covered:**

- Provider comparison
- Migration procedures
- Configuration differences
- Performance considerations
- Rollback strategies

---

## Contributing to Documentation

Found an error or want to add to these guides? Check out our
[contribution guide](/guides/contributing/) to learn how you can help improve
the documentation.

## Quick Reference

- **[CLI Commands](/api/cli/)** - Complete command reference
- **[Configuration Options](/api/configuration/)** - All configuration
  parameters
- **[Troubleshooting](/troubleshooting/)** - Problem-solving resources
- **[FAQ](/troubleshooting/faq/)** - Frequently asked questions
