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
        source: '/analytics',
        destination: 'http://127.0.0.1:8000/analytics',
      },
      {
        source: '/api/escalations',
        destination: 'http://127.0.0.1:8000/api/escalations',
      },
      {
        source: '/api/escalations/:path*',
        destination: 'http://127.0.0.1:8000/api/escalations/:path*',
      },
      {
        source: '/api/call-stats',
        destination: 'http://127.0.0.1:8000/api/call-stats',
      },
      {
        source: '/api/recent-calls',
        destination: 'http://127.0.0.1:8000/api/recent-calls',
      },
    ];
  },
};

export default nextConfig;
