/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: [
    "@gridtrace/api-client",
    "@gridtrace/charts",
    "@gridtrace/config",
    "@gridtrace/contracts",
    "@gridtrace/domain",
    "@gridtrace/maps",
    "@gridtrace/testing",
    "@gridtrace/ui",
  ],
};

export default nextConfig;
