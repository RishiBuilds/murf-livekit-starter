import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  eslint: {
    // These warnings come from upstream LiveKit/AI UI components, not our code.
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: '/escalations',
        destination: 'http://127.0.0.1:8000/',
      },
      {
        source: '/dashboard',
        destination: 'http://127.0.0.1:8000/',
      },
      {
        source: '/api/escalations',
        destination: 'http://127.0.0.1:8000/api/escalations',
      },
      {
        source: '/api/escalations/:path*',
        destination: 'http://127.0.0.1:8000/api/escalations/:path*',
      },
    ];
  },
};

export default nextConfig;
