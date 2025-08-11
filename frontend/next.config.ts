import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async headers() {

    return [
      {
        source: '/(.*)', 
        headers: [
          {
            key: 'X-Content-Type-Options', 
            value: 'nosniff' 
          }, 
          {
            key: 'X-Frame-Options', 
            value: 'DENY' 
          }, 
          {
            key: 'X-XSS-Protection', 
            value: '1; mode = block' 
          }, 
          {
            key: 'Strict-Transport-Security', 
            value: 'max-age='
          }
        ]
      }
    ]

  }
};

export default nextConfig;
