/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverComponentsExternalPackages: ["better-sqlite3", "tesseract.js", "tesseract.js-core", "pdf-parse", "exifr"],
  },
};

export default nextConfig;
