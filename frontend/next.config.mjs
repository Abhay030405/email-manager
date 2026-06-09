/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In production DO App Platform, ingress routes /api/* to the backend.
    // Rewrites are only needed in local development to proxy to the backend.
    if (process.env.NODE_ENV === "production") return [];

    const apiBase =
      process.env.NEXT_PUBLIC_API_URL?.split(",")[0]?.trim() ??
      "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
