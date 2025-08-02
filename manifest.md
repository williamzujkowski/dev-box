# dev-box Project Manifest

## Project Overview

**dev-box** is a comprehensive development environment platform that provides
isolated Ubuntu 24.04 development environments using Vagrant, VirtualBox, and
Libvirt/KVM virtualization technologies.

## Documentation Structure

### Primary Documentation

- **`docs/dev-box-site/`** - Main documentation site built with Eleventy
  - **Purpose**: Comprehensive user-facing documentation
  - **Technology**: Eleventy static site generator
  - **Content**: Installation guides, user tutorials, API reference,
    troubleshooting
  - **Deployment**: Static site suitable for GitHub Pages or any web host

### Configuration Documentation

- **`CLAUDE.md`** - Claude Code integration and SPARC workflow configuration

  - **Purpose**: Development workflow optimization for AI-assisted coding
  - **Features**: Parallel execution patterns, agent coordination, performance
    optimization
  - **Integration**: Links to main documentation site for project-specific
    content

- **`README.md`** - Repository overview and quick start guide

  - **Purpose**: Repository entry point with essential information
  - **Content**: Quick start instructions, feature overview, documentation links
  - **Design**: Minimal content that redirects to comprehensive docs site

- **`manifest.md`** - This file, documenting project structure and organization
  - **Purpose**: Project documentation strategy and file organization
  - **Audience**: Contributors and maintainers

## File Organization

### Root Level Files

```
├── README.md              # Repository overview and quick start
├── CLAUDE.md              # Claude Code workflow configuration
├── manifest.md            # Project structure documentation
├── Vagrantfile            # Vagrant configuration
├── .gitignore             # Git ignore patterns
└── package.json           # Node.js dependencies (if any)
```

### Documentation Site Structure

```
docs/dev-box-site/
├── eleventy.config.js     # Eleventy configuration
├── package.json           # Documentation site dependencies
├── package-lock.json      # Locked dependencies
├── src/                   # Source content and templates
│   ├── _data/             # Global data files
│   │   └── site.json      # Site configuration and metadata
│   ├── _layouts/          # Page templates
│   │   ├── base.njk       # Base layout template
│   │   ├── guide.njk      # Guide page template
│   │   └── page.njk       # Standard page template
│   ├── index.njk          # Homepage template
│   ├── getting-started/   # Installation and setup guides
│   │   └── index.md       # Getting started overview
│   ├── guides/            # User guides and tutorials
│   │   ├── index.md       # Guides overview
│   │   ├── libvirt-setup.md
│   │   └── vagrant-workflow.md
│   ├── api/               # API reference documentation
│   │   └── index.md       # API overview
│   ├── troubleshooting/   # Problem-solving guides
│   │   └── index.md       # Troubleshooting overview
│   └── assets/            # Static assets
│       ├── css/           # Stylesheets
│       │   ├── main.css
│       │   └── prism.css  # Code syntax highlighting
│       └── js/            # JavaScript files
│           └── main.js
└── _site/                 # Generated static site (build output)
```

### Development Workflow Files

```
├── .claude-flow/          # Claude Flow coordination metrics
├── .swarm/                # Swarm coordination memory
├── scripts/               # Automation and provisioning scripts
├── tests/                 # Test suites
└── .github/               # GitHub Actions and templates
    ├── workflows/         # CI/CD pipelines
    ├── ISSUE_TEMPLATE/    # Issue templates
    └── PULL_REQUEST_TEMPLATE.md
```

## Documentation Philosophy

### Single Source of Truth

The **`docs/dev-box-site/`** serves as the authoritative documentation source.
All other documentation files either:

1. Provide minimal essential information with links to the full docs
2. Cover development-specific workflows (like CLAUDE.md)
3. Document meta-information about the project structure (like this manifest)

### Avoiding Duplication

- **README.md**: Brief overview + links to docs site
- **CLAUDE.md**: Development workflow + links to relevant docs sections
- **docs/dev-box-site/**: Comprehensive documentation covering all user needs

### Maintenance Strategy

- **Primary Content**: Update documentation site content for user-facing changes
- **References**: Update cross-references when structure changes
- **Workflow Docs**: Update CLAUDE.md for development process changes
- **Manifest**: Update this file when project structure evolves

## Content Guidelines

### Documentation Site Content

- **User-focused**: Written for developers using dev-box
- **Comprehensive**: Covers installation, usage, troubleshooting, and reference
- **Searchable**: Well-structured with clear navigation
- **Examples**: Includes code examples and step-by-step instructions

### Configuration Documentation

- **Developer-focused**: Written for contributors and maintainers
- **Workflow-specific**: Covers development processes and tool integration
- **Cross-referenced**: Links to relevant sections in main documentation

### Repository Documentation

- **Concise**: Essential information only
- **Welcoming**: Clear entry point for new users
- **Directing**: Guides users to appropriate detailed documentation

## Technology Stack

### Documentation Site

- **Generator**: Eleventy (11ty) - Static site generator
- **Templates**: Nunjucks templating engine
- **Styling**: Custom CSS with modern design patterns
- **Syntax Highlighting**: Prism.js for code blocks
- **Navigation**: Eleventy Navigation plugin
- **Markdown**: Enhanced with markdown-it plugins

### Development Tools

- **Version Control**: Git with GitHub
- **CI/CD**: GitHub Actions for automated builds and deployment
- **Code Quality**: ESLint, Prettier for consistent formatting
- **Testing**: Automated validation of documentation links and structure

## Deployment Strategy

### Documentation Site Deployment

1. **Build Process**: Eleventy generates static site to `_site/` directory
2. **Hosting Options**:
   - GitHub Pages (recommended for open source)
   - Netlify (for advanced features)
   - Any static hosting service
3. **Domain**: Can be hosted at custom domain or GitHub Pages subdomain

### Maintenance Workflow

1. **Content Updates**: Edit markdown files in `src/` directory
2. **Local Development**: Use `npm run dev` for live preview
3. **Build**: Use `npm run build` to generate production site
4. **Deployment**: Automated via GitHub Actions or manual deployment

## Future Considerations

### Planned Enhancements

- **Search**: Add search functionality to documentation site
- **Versioning**: Version-specific documentation for major releases
- **Internationalization**: Multi-language support if needed
- **Interactive Examples**: Embedded code playgrounds for configuration examples

### Scalability

- **Modular Content**: Documentation structure supports easy content addition
- **Template System**: Consistent layouts enable rapid page creation
- **Asset Management**: Organized asset structure supports growth
- **Performance**: Static site generation ensures fast loading times

---

_Last updated: 2025-08-02_ _For questions about this manifest or project
structure, please refer to the [main documentation site](docs/dev-box-site/)._
