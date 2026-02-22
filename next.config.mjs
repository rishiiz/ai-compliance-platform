/** @type {import('next').NextConfig} */
const nextConfig = {
  // Reduce bundle size: tree-shake lucide-react and other barrel imports
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  // Compress responses (default in production)
  compress: true,
};

export default nextConfig;
