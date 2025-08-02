const { EleventyNavigationPlugin } = require("@11ty/eleventy-navigation");
const markdownIt = require("markdown-it");
const markdownItAnchor = require("markdown-it-anchor");
const markdownItToc = require("markdown-it-table-of-contents");

module.exports = function (eleventyConfig) {
  // Add plugins
  eleventyConfig.addPlugin(EleventyNavigationPlugin);

  // Configure markdown
  const markdownItOptions = {
    html: true,
    breaks: true,
    linkify: true,
  };

  const markdownLib = markdownIt(markdownItOptions)
    .use(markdownItAnchor, {
      permalink: markdownItAnchor.permalink.headerLink({
        safariReaderFix: true,
        class: "header-anchor",
      }),
    })
    .use(markdownItToc, {
      includeLevel: [2, 3, 4],
      containerClass: "table-of-contents",
      markerPattern: /^\[\[toc\]\]/im,
    });

  eleventyConfig.setLibrary("md", markdownLib);

  // Copy static assets
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy("src/images");

  // Add collections
  eleventyConfig.addCollection("guides", function (collectionApi) {
    return collectionApi.getFilteredByGlob("src/guides/**/*.md");
  });

  eleventyConfig.addCollection("troubleshooting", function (collectionApi) {
    return collectionApi.getFilteredByGlob("src/troubleshooting/**/*.md");
  });

  eleventyConfig.addCollection("api", function (collectionApi) {
    return collectionApi.getFilteredByGlob("src/api/**/*.md");
  });

  // Add custom filters
  eleventyConfig.addFilter("dateDisplay", function (dateObj) {
    return new Date(dateObj).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  });

  eleventyConfig.addFilter("excerpt", function (content, limit = 150) {
    const text = content.replace(/<[^>]*>/g, "");
    return text.length > limit ? `${text.substr(0, limit)  }...` : text;
  });

  // Add shortcodes
  eleventyConfig.addShortcode("currentYear", () => new Date().getFullYear());

  eleventyConfig.addPairedShortcode("alert", function (content, type = "info") {
    return `<div class="alert alert-${type}" role="alert">
      <div class="alert-content">${content}</div>
    </div>`;
  });

  eleventyConfig.addPairedShortcode("codeblock", function (content, language = "") {
    return `<div class="code-block">
      <pre><code class="language-${language}">${content}</code></pre>
    </div>`;
  });

  // Configure input/output directories
  return {
    dir: {
      input: "src",
      includes: "_includes",
      layouts: "_layouts",
      data: "_data",
      output: "_site",
    },
    templateFormats: ["md", "njk", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
    dataTemplateEngine: "njk",
  };
};
