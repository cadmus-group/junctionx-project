import next from "@gridtrace/eslint-config/next";

export default [
  ...next,
  {
    ignores: [".next/**", "node_modules/**", "playwright-report/**", "test-results/**"],
  },
];
