# Prompt Templates for Claude-Flow

This directory contains reusable prompt templates for automating common development workflows with Claude-Flow.

## Available Templates

### 1. `commit_and_vagrant_smoke_test_prompt.md`
- **Purpose**: Commit changes and run smoke test on Ubuntu 24.04 VM via Vagrant
- **Features**: Self-heals common provisioning issues, verifies SSH connectivity
- **Usage**: `npx claude-flow@alpha swarm --template prompt-templates/commit_and_vagrant_smoke_test_prompt.md "Verify Ubuntu 24.04 VM"`

### 2. `commit_and_test_all_providers.md`
- **Purpose**: Test both Vagrant and Docker environments for Ubuntu 24.04
- **Features**: Dual provider support, graceful degradation if one unavailable
- **Usage**: `npx claude-flow@alpha swarm --template .llmconfig/prompt-templates/commit_and_test_all_providers.md "Verify all providers"`

### 3. `install_and_smoke_test_vm.md`
- **Purpose**: Install VirtualBox + Vagrant on host and set up Ubuntu 24.04 VM
- **Features**: Full host setup, repository configuration, user permissions
- **Usage**: `npx claude-flow@alpha swarm --template .llmconfig/prompt-templates/install_and_smoke_test_vm.md "Install and test VM"`

## Common Self-Healing Patterns

All templates include automatic fixes for:
- Missing `linux-headers-$(uname -r)` for kernel modules
- Missing `dkms` for dynamic kernel module support
- Missing `build-essential` for compilation tools
- Incorrect or unavailable Vagrant box names
- VirtualBox Guest Additions build failures

## Best Practices

1. **Always commit before testing** - Templates include pre-flight commits
2. **Use structured logging** - All templates output clear status messages
3. **Push only when ready** - Manual push control for safety
4. **Adapt to environment** - Templates gracefully handle missing tools

## Integration with CI/CD

These templates can be integrated into GitHub Actions or other CI systems:

```yaml
- name: Run VM Smoke Test
  run: |
    npx claude-flow@alpha swarm \
      --template .llmconfig/prompt-templates/commit_and_test_all_providers.md \
      "Verify CI environment"
```

## Contributing

When adding new templates:
1. Follow the existing format and structure
2. Include clear behavioral requirements
3. Add self-healing logic for common failures
4. Document usage in this README
5. Test the template before committing