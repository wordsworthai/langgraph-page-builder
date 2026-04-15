import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = __dirname
const backendDir = path.resolve(__dirname, '../backend')

export default defineConfig({
  plugins: [react()],
  root: frontendDir,
  css: {
    postcss: {
      plugins: [
        tailwindcss({ config: path.resolve(frontendDir, 'tailwind.config.js') }),
        autoprefixer(),
      ],
    },
  },
  resolve: {
    // Dependencies live in frontend/node_modules
    alias: {
      '@code_editor': path.resolve(frontendDir, 'code_editor'),
      'react': path.resolve(frontendDir, 'node_modules/react'),
      'react/jsx-runtime': path.resolve(frontendDir, 'node_modules/react/jsx-runtime'),
      'react/jsx-dev-runtime': path.resolve(frontendDir, 'node_modules/react/jsx-dev-runtime'),
      'react-dom': path.resolve(frontendDir, 'node_modules/react-dom'),
      'react-dom/client': path.resolve(frontendDir, 'node_modules/react-dom/client'),
      'vis-network': path.resolve(frontendDir, 'node_modules/vis-network'),
      'vis-data': path.resolve(frontendDir, 'node_modules/vis-data'),
      'lucide-react': path.resolve(frontendDir, 'node_modules/lucide-react'),
      'react-toastify': path.resolve(frontendDir, 'node_modules/react-toastify'),
      'react-toastify/dist/ReactToastify.css': path.resolve(frontendDir, 'node_modules/react-toastify/dist/ReactToastify.css'),
      '@monaco-editor/react': path.resolve(frontendDir, 'node_modules/@monaco-editor/react'),
    },
  },
  server: {
    host: '0.0.0.0', // Listen on all network interfaces
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: path.resolve(backendDir, 'dist'),
  }
})
