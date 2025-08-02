module.exports = {
  env: {
    node: true,
    es2021: true,
    browser: true,
  },
  extends: [
    "eslint:recommended",
    "prettier", // Disable ESLint rules that conflict with Prettier
  ],
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: "module",
  },
  rules: {
    // Best practices
    "no-console": "warn",
    "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "no-var": "error",
    "prefer-const": "error",

    // Style rules (handled by Prettier)
    indent: "off",
    quotes: "off",
    semi: "off",
    "comma-dangle": "off",
    "max-len": "off",

    // Additional quality rules
    eqeqeq: ["error", "always"],
    curly: ["error", "all"],
    "no-eval": "error",
    "no-implied-eval": "error",
    "prefer-template": "error",
    "no-useless-concat": "error",
  },
  overrides: [
    {
      files: ["*.config.js", "*.conf.js"],
      env: {
        node: true,
      },
      rules: {
        "no-console": "off",
      },
    },
  ],
};
