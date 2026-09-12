/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The browser never talks to Laravel directly: requests go through Next's
  // server so the session cookie and the API token stay out of client code.
  async rewrites() {
    return [
      {
        source: '/api/laravel/:path*',
        destination: `${process.env.LARAVEL_API_URL ?? 'http://api:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
