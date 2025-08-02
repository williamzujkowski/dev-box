/**
 * dev-box Documentation Site JavaScript
 */

(function () {
  "use strict";

  // Mobile menu functionality
  function initMobileMenu() {
    const mobileMenuToggle = document.querySelector(".mobile-menu-toggle");
    const mainNav = document.querySelector(".main-nav");

    if (!mobileMenuToggle || !mainNav) {return;}

    mobileMenuToggle.addEventListener("click", function () {
      const isExpanded = this.getAttribute("aria-expanded") === "true";
      this.setAttribute("aria-expanded", !isExpanded);
      mainNav.classList.toggle("nav-open");

      // Toggle hamburger animation
      this.classList.toggle("menu-open");
    });

    // Close menu when clicking outside
    document.addEventListener("click", function (e) {
      if (!mobileMenuToggle.contains(e.target) && !mainNav.contains(e.target)) {
        mobileMenuToggle.setAttribute("aria-expanded", "false");
        mainNav.classList.remove("nav-open");
        mobileMenuToggle.classList.remove("menu-open");
      }
    });

    // Close menu on escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        mobileMenuToggle.setAttribute("aria-expanded", "false");
        mainNav.classList.remove("nav-open");
        mobileMenuToggle.classList.remove("menu-open");
      }
    });
  }

  // Smooth scrolling for anchor links
  function initSmoothScrolling() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');

    anchorLinks.forEach(link => {
      link.addEventListener("click", function (e) {
        const targetId = this.getAttribute("href");
        if (targetId === "#") {return;}

        const targetElement = document.querySelector(targetId);
        if (!targetElement) {return;}

        e.preventDefault();

        const headerHeight = document.querySelector(".site-header")?.offsetHeight || 0;
        const targetPosition = targetElement.offsetTop - headerHeight - 20;

        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        });

        // Update URL without triggering scroll
        history.pushState(null, null, targetId);
      });
    });
  }

  // Copy code functionality
  function initCodeCopy() {
    const codeBlocks = document.querySelectorAll('pre[class*="language-"]');

    codeBlocks.forEach(block => {
      const wrapper = document.createElement("div");
      wrapper.className = "code-block-wrapper";
      block.parentNode.insertBefore(wrapper, block);
      wrapper.appendChild(block);

      const copyButton = document.createElement("button");
      copyButton.className = "copy-code-button";
      copyButton.innerHTML = "📋 Copy";
      copyButton.setAttribute("aria-label", "Copy code to clipboard");

      wrapper.appendChild(copyButton);

      copyButton.addEventListener("click", async () => {
        const code = block.querySelector("code");
        const text = code.textContent;

        try {
          await navigator.clipboard.writeText(text);
          copyButton.innerHTML = "✅ Copied!";
          copyButton.classList.add("copied");

          setTimeout(() => {
            copyButton.innerHTML = "📋 Copy";
            copyButton.classList.remove("copied");
          }, 2000);
        } catch (err) {
          // Fallback for browsers that don't support clipboard API
          const textArea = document.createElement("textarea");
          textArea.value = text;
          document.body.appendChild(textArea);
          textArea.select();
          document.execCommand("copy");
          document.body.removeChild(textArea);

          copyButton.innerHTML = "✅ Copied!";
          setTimeout(() => {
            copyButton.innerHTML = "📋 Copy";
          }, 2000);
        }
      });
    });
  }

  // Table of contents active link highlighting
  function initTocHighlighting() {
    const tocLinks = document.querySelectorAll(".table-of-contents a");
    const headings = document.querySelectorAll("h2[id], h3[id], h4[id]");

    if (tocLinks.length === 0 || headings.length === 0) {return;}

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          const id = entry.target.getAttribute("id");
          const tocLink = document.querySelector(`.table-of-contents a[href="#${id}"]`);

          if (entry.isIntersecting) {
            // Remove active class from all links
            tocLinks.forEach(link => link.classList.remove("active"));
            // Add active class to current link
            if (tocLink) {tocLink.classList.add("active");}
          }
        });
      },
      {
        rootMargin: "-20% 0% -80% 0%",
      }
    );

    headings.forEach(heading => observer.observe(heading));
  }

  // Search functionality (if search is implemented)
  function initSearch() {
    const searchInput = document.querySelector("#search-input");
    const searchResults = document.querySelector("#search-results");

    if (!searchInput || !searchResults) {return;}

    let searchTimeout;

    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimeout);
      const query = this.value.trim();

      if (query.length < 2) {
        searchResults.innerHTML = "";
        searchResults.classList.remove("has-results");
        return;
      }

      searchTimeout = setTimeout(() => {
        performSearch(query);
      }, 300);
    });

    function performSearch(query) {
      // This would typically integrate with a search service
      // For now, we'll show a placeholder
      searchResults.innerHTML = `
        <div class="search-message">
          Search functionality will be implemented with a search service.
          Looking for: "${query}"
        </div>
      `;
      searchResults.classList.add("has-results");
    }
  }

  // Theme switcher (if dark mode toggle is added)
  function initThemeSwitcher() {
    const themeToggle = document.querySelector("#theme-toggle");
    if (!themeToggle) {return;}

    const currentTheme = localStorage.getItem("theme") || "auto";
    document.documentElement.setAttribute("data-theme", currentTheme);

    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme");
      let newTheme;

      switch (currentTheme) {
        case "light":
          newTheme = "dark";
          break;
        case "dark":
          newTheme = "auto";
          break;
        default:
          newTheme = "light";
      }

      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
    });
  }

  // Back to top button
  function initBackToTop() {
    const backToTopButton = document.createElement("button");
    backToTopButton.className = "back-to-top";
    backToTopButton.innerHTML = "↑";
    backToTopButton.setAttribute("aria-label", "Back to top");
    backToTopButton.style.display = "none";
    document.body.appendChild(backToTopButton);

    window.addEventListener("scroll", () => {
      if (window.pageYOffset > 300) {
        backToTopButton.style.display = "flex";
      } else {
        backToTopButton.style.display = "none";
      }
    });

    backToTopButton.addEventListener("click", () => {
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });
  }

  // External link indicators
  function initExternalLinks() {
    const externalLinks = document.querySelectorAll(
      `a[href^="http"]:not([href*="${  window.location.hostname  }"])`
    );

    externalLinks.forEach(link => {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");

      // Add external link icon
      if (!link.querySelector(".external-icon")) {
        const icon = document.createElement("span");
        icon.className = "external-icon";
        icon.innerHTML = " ↗";
        icon.setAttribute("aria-hidden", "true");
        link.appendChild(icon);
      }
    });
  }

  // Form enhancements (if forms are present)
  function initFormEnhancements() {
    const forms = document.querySelectorAll("form");

    forms.forEach(form => {
      const inputs = form.querySelectorAll("input, textarea, select");

      inputs.forEach(input => {
        // Add floating label effect
        if (input.type !== "submit" && input.type !== "button") {
          input.addEventListener("focus", () => {
            input.parentElement.classList.add("focused");
          });

          input.addEventListener("blur", () => {
            if (!input.value) {
              input.parentElement.classList.remove("focused");
            }
          });

          // Check if input has value on page load
          if (input.value) {
            input.parentElement.classList.add("focused");
          }
        }
      });
    });
  }

  // Initialize all functionality when DOM is ready
  function init() {
    initMobileMenu();
    initSmoothScrolling();
    initCodeCopy();
    initTocHighlighting();
    initSearch();
    initThemeSwitcher();
    initBackToTop();
    initExternalLinks();
    initFormEnhancements();

    // Add page loaded class for CSS animations
    document.body.classList.add("page-loaded");
  }

  // Start initialization
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // CSS for dynamically created elements
  const styles = `
    .code-block-wrapper {
      position: relative;
    }
    
    .copy-code-button {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 0.25rem;
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
      cursor: pointer;
      opacity: 0;
      transition: opacity 0.2s ease-in-out;
      z-index: 10;
    }
    
    .code-block-wrapper:hover .copy-code-button {
      opacity: 1;
    }
    
    .copy-code-button:hover {
      background: rgba(0, 0, 0, 0.9);
    }
    
    .copy-code-button.copied {
      background: #10b981;
      border-color: #10b981;
    }
    
    .back-to-top {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      width: 3rem;
      height: 3rem;
      background: var(--color-primary);
      color: white;
      border: none;
      border-radius: 50%;
      font-size: 1.5rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--shadow-lg);
      transition: all 0.2s ease-in-out;
      z-index: 100;
    }
    
    .back-to-top:hover {
      background: var(--color-primary-dark);
      transform: translateY(-2px);
    }
    
    .external-icon {
      opacity: 0.7;
      font-size: 0.8em;
    }
    
    .table-of-contents a.active {
      color: var(--color-primary);
      font-weight: 500;
    }
    
    @media (max-width: 767px) {
      .back-to-top {
        bottom: 1rem;
        right: 1rem;
        width: 2.5rem;
        height: 2.5rem;
        font-size: 1.25rem;
      }
    }
  `;

  const styleSheet = document.createElement("style");
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
})();
