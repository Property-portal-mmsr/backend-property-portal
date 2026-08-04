// PM2 Ecosystem Configuration for MakeMyStay Realty Employee Portal
// Manages two processes:
//   - employee-api:    FastAPI backend on port 8005
//   - employee-portal: Next.js frontend on port 3005

module.exports = {
  apps: [
    {
      name: "employee-api",
      script: "/var/www/property-portal-backend/venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8005 --workers 2",
      cwd: "/var/www/property-portal-backend",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
        PYTHONPATH: "/var/www/property-portal-backend",
      },
    },
    {
      name: "employee-portal",
      script: "npm",
      args: "start",
      cwd: "/var/www/employee-portal",
      env: {
        PORT: 3005,
        NODE_ENV: "production",
        NEXT_PUBLIC_API_URL: "https://employee-api.makemystay.ai/api/v1",
      },
    },
  ],
};
