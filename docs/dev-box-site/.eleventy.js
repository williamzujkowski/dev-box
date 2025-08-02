module.exports = function(eleventyConfig) {
  // Copy static assets
  eleventyConfig.addPassthroughCopy("src/assets");
  
  // Set directories
  return {
    dir: {
      input: "src",
      includes: "_includes", 
      layouts: "_layouts",
      data: "_data",
      output: "_site"
    },
    templateFormats: ["md", "njk", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk"
  };
};