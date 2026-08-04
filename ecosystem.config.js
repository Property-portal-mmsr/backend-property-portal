// PM2 Ecosystem Configuration for MakeMyStay Realty Employee Portal
//
// NOTE: Your backend API (api.makemystay.ai on port 8000) is already managed
// by your existing "makemystay-api" PM2 process.
//
// This configuration launches the new Next.js Employee Portal frontend on port 3005.

module.exports = {
  apps: [
    {
      name: "employee-portal",
      script: "npm",
      args: "start",
      cwd: "/var/www/employee-portal",
      env: {
        PORT: 3005,
        NEXT_PUBLIC_API_URL: "₹"
      }
    }
  ]
};
