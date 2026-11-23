import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "src/contracts/**",
      "next-env.d.ts",
      "test-results/**",
      "playwright-report/**",
      "*.mjs",
    ],
  },
  ...tseslint.configs.strict,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },
);
