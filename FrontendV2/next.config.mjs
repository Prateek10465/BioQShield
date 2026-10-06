/** @type {import('next').NextConfig} */
const isExport = process.env.NEXT_EXPORT === 'true'
const apiDestination = process.env.BIOQSHIELD_API_URL || 'http://127.0.0.1:8001'

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
  // In dev mode (pnpm dev), proxy API requests to the FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiDestination}/api/:path*`,
      },
    ]
  },
  ...(isExport ? { output: 'export' } : {}),
}

export default nextConfig

