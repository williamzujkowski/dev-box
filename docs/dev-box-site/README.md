# dev-box Documentation Site

A comprehensive, interactive documentation site for the dev-box development
environment platform, built with [Eleventy](https://11ty.dev).

## Features

- **Modern Design**: Clean, responsive design with professional branding
- **Fast Performance**: Optimized for speed with minimal JavaScript and
  efficient CSS
- **Accessibility**: WCAG 2.1 AA compliant with screen reader support
- **Interactive Elements**: Copy-to-clipboard code blocks, smooth scrolling, and
  mobile-friendly navigation
- **Search Functionality**: Fast client-side search (to be implemented)
- **CI Integration**: Automated building with incremental builds for faster
  deployment

## Local Development

### Prerequisites

- Node.js 16+
- npm or yarn

### Getting Started

```bash
# Install dependencies
npm install

# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Build with incremental optimization
npm run build:incremental

# Clean build directory
npm run clean
```

### Development Server

The development server runs at `http://localhost:8080` with:

- Hot reload for content changes
- Automatic browser refresh
- File watching for all source files

## Project Structure

```
src/
├── _data/           # Global data files (site.json)
├── _includes/       # Reusable components
├── _layouts/        # Page templates
│   ├── base.njk     # Base layout with navigation
│   ├── page.njk     # Standard page layout
│   └── guide.njk    # Guide-specific layout
├── assets/          # Static assets
│   ├── css/         # Stylesheets
│   ├── js/          # JavaScript
│   └── images/      # Images and icons
├── getting-started/ # Getting started content
├── guides/          # User guides
├── api/             # API reference
├── troubleshooting/ # Troubleshooting guides
└── index.njk        # Homepage

# Generated output
_site/              # Built site (git ignored)

# Configuration
eleventy.config.js  # Eleventy configuration
package.json        # Dependencies and scripts
.eleventyignore     # Files to ignore during build
```

## Content Creation

### Adding New Pages

1. Create a new `.md` file in the appropriate directory
2. Add frontmatter with required metadata:

```yaml
---
layout: page.njk
title: "Your Page Title"
description: "Page description for SEO"
eleventyNavigation:
  key: Page Title
  parent: Parent Section # Optional
  order: 1 # Optional
---
# Your Content Here
```

### Guide Pages

For guides, use the `guide.njk` layout:

```yaml
---
layout: guide.njk
title: "Guide Title"
description: "Guide description"
eleventyNavigation:
  key: Guide Title
  parent: Guides
  order: 1
difficulty: beginner # beginner, intermediate, advanced
estimatedTime: "30 minutes"
toc: true # Enable table of contents
---
```

### Navigation

Navigation is automatically generated from the `eleventyNavigation` frontmatter.
The structure follows:

- **Key**: Display name in navigation
- **Parent**: Parent section (creates hierarchical nav)
- **Order**: Sort order within section

### Code Blocks

Use fenced code blocks with language specification:

````markdown
```bash
# This is a bash command
vagrant up
```

```javascript
// This is JavaScript
const app = express();
```
````

### Alerts and Callouts

Use shortcodes for special content:

```markdown
{% alert "info" %} This is an informational alert. {% endalert %}

{% alert "warning" %} This is a warning message. {% endalert %}

{% alert "error" %} This is an error message. {% endalert %}

{% alert "success" %} This is a success message. {% endalert %}
```

### Table of Contents

Add table of contents to any page:

```yaml
---
toc: true
---
# Your content

[[toc]] # This generates the TOC
```

## Styling Guide

### CSS Architecture

The CSS follows a modular approach:

- **CSS Custom Properties**: All colors, spacing, and typography defined as
  variables
- **Mobile-First**: Responsive design starting from mobile
- **Component-Based**: Styles organized by component type
- **Performance**: Minimal CSS with efficient selectors

### Design System

```css
/* Colors */
--color-primary: #2563eb;
--color-secondary: #7c3aed;
--color-accent: #06b6d4;

/* Typography */
--font-family-sans: "Inter", sans-serif;
--font-family-mono: "JetBrains Mono", monospace;

/* Spacing */
--space-1: 0.25rem;
--space-4: 1rem;
--space-8: 2rem;
```

### Component Classes

- `.btn` - Button styles with variants (`.btn--primary`, `.btn--secondary`)
- `.alert` - Alert boxes with types (`.alert-info`, `.alert-warning`)
- `.feature-card` - Feature highlight cards
- `.code-block` - Code block wrappers
- `.nav-link` - Navigation link styles

## JavaScript Features

### Functionality

- **Mobile Navigation**: Responsive hamburger menu
- **Smooth Scrolling**: Anchor link smooth scrolling
- **Copy Code**: One-click code copying to clipboard
- **Table of Contents**: Active section highlighting
- **Back to Top**: Scroll-to-top button
- **External Links**: Automatic external link indicators

### Adding JavaScript

Minimal JavaScript approach - only add what's necessary:

```javascript
// Add to src/assets/js/main.js
function newFeature() {
  // Your feature code
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", newFeature);
```

## Performance Optimization

### Build Performance

- **Incremental Builds**: Use `npm run build:incremental` for faster rebuilds
- **Efficient Ignoring**: `.eleventyignore` excludes unnecessary files
- **Image Optimization**: Images optimized for web delivery
- **CSS/JS Minification**: Automatic minification in production builds

### Runtime Performance

- **Minimal JavaScript**: Core functionality only
- **Efficient CSS**: Optimized selectors and minimal unused styles
- **Font Loading**: Efficient web font loading strategy
- **Image Optimization**: Responsive images and modern formats

### Performance Budget

- **Total Size**: < 50MB
- **CSS**: < 50KB
- **JavaScript**: < 100KB
- **Lighthouse Score**: > 90 for all categories

## CI/CD Integration

### GitHub Actions

The site includes comprehensive CI/CD:

- **Build Verification**: Ensures all builds complete successfully
- **Link Checking**: Validates internal links aren't broken
- **Accessibility Testing**: Runs pa11y and axe for accessibility compliance
- **Performance Testing**: Lighthouse CI for performance monitoring
- **Deployment**: Automatic deployment to GitHub Pages on main branch

### Build Commands for CI

```bash
# Standard build
npm run build

# Incremental build (faster for CI)
npm run build:incremental

# Development build with watching
npm run dev
```

## Accessibility

### Standards Compliance

- **WCAG 2.1 AA**: Full compliance with accessibility guidelines
- **Semantic HTML**: Proper heading hierarchy and landmark regions
- **Screen Reader Support**: ARIA labels and descriptions
- **Keyboard Navigation**: Full keyboard accessibility
- **Color Contrast**: Meets contrast ratio requirements

### Testing

```bash
# Run accessibility tests
pa11y-ci --sitemap http://localhost:8080/sitemap.xml
axe _site/index.html _site/getting-started/index.html
```

## SEO Optimization

### Meta Tags

All pages include:

- Title and description meta tags
- Open Graph tags for social sharing
- Twitter Card tags
- Canonical URLs

### Structure

- Semantic HTML structure
- Proper heading hierarchy (H1 → H2 → H3)
- Internal linking strategy
- Sitemap generation

## Content Guidelines

### Writing Style

- **Clear and Concise**: Direct, actionable language
- **User-Focused**: Address the user directly ("you")
- **Consistent Terminology**: Use the same terms throughout
- **Code Examples**: Provide working examples for all concepts

### Content Structure

1. **Introduction**: What the page covers
2. **Prerequisites**: What users need to know/have
3. **Step-by-Step Instructions**: Clear, numbered steps
4. **Examples**: Working code examples
5. **Troubleshooting**: Common issues and solutions
6. **Next Steps**: Where to go from here

### Code Examples

- Always include working, tested examples
- Provide context for each example
- Use realistic variable names and scenarios
- Include error handling where appropriate

## Deployment

### GitHub Pages

Automatic deployment on push to main branch:

1. Build runs in GitHub Actions
2. Site deploys to `https://dev-box-docs.github.io/docs/`
3. Custom domain configured via CNAME

### Manual Deployment

```bash
# Build the site
npm run build

# Deploy to any static hosting
rsync -av _site/ user@server:/path/to/web/root/
```

## Troubleshooting

### Common Issues

**Build fails with plugin errors:**

```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**Images not loading:**

- Check image paths are relative to source files
- Ensure images are in `src/assets/images/`
- Verify passthrough copy configuration

**Styles not updating:**

- Check for CSS syntax errors
- Clear browser cache
- Restart development server

### Debug Mode

```bash
# Enable Eleventy debug mode
DEBUG=Eleventy* npm run build

# Verbose output
npm run build -- --verbose
```

## Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

### Content Contributions

- Follow the content guidelines
- Test all code examples
- Check for accessibility issues
- Verify mobile responsiveness

### Development Contributions

- Follow existing code patterns
- Update documentation for new features
- Add tests where appropriate
- Ensure CI passes

## License

This documentation site is part of the dev-box project and follows the same
license terms.

---

## Quick Reference

```bash
# Development
npm run dev                    # Start dev server
npm run build                  # Build for production
npm run build:incremental      # Incremental build
npm run clean                  # Clean build directory

# Testing
npm test                       # Run tests (if available)
pa11y-ci --sitemap <url>      # Accessibility testing
lighthouse-ci                 # Performance testing

# Deployment
git push origin main          # Auto-deploy via GitHub Actions
```

For questions or support, please check the
[main dev-box documentation](../../README.md) or open an issue in the GitHub
repository.
