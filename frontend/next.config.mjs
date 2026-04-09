/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    // API_URL_INTERNAL은 빌드 타임 ARG로 주입 (standalone에서 runtime env 미지원)
    const apiTarget = process.env.API_URL_INTERNAL ?? 'http://api:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
