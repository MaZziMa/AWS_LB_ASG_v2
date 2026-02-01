import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const defaultTarget = 'http://course-management-alb-dev-1530526851.us-east-1.elb.amazonaws.com'
  const target = env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || defaultTarget

  const mkProxy = () => ({
    target,
    changeOrigin: true,
  })

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        // Bedrock agent endpoints live under /api/* on the backend.
        '/api': mkProxy(),

        // DynamoDB-backed REST endpoints live at the backend root.
        '/courses': mkProxy(),
        '/students': mkProxy(),
        '/enrollments': mkProxy(),
        '/health': mkProxy(),
        '/cpu-burn': mkProxy(),
      },
    },
  }
})
