import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: '../static/portal',
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: 'src/main.tsx',
      output: {
        entryFileNames: 'app.js',
        assetFileNames: (asset) => asset.names.some(name => name.endsWith('.css')) ? 'style.css' : 'assets/[name]-[hash][extname]',
      },
    },
    manifest: false,
  },
})
