import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/main.jsx'),
      name: 'HecosFlowsCanvas',
      fileName: 'flows_canvas',
      formats: ['iife'],
    },
    outDir: resolve(__dirname, '../dist'),
    emptyOutDir: false,
    rollupOptions: {
      output: {
        // Single bundle file, no chunking
        inlineDynamicImports: true,
        entryFileNames: 'flows_canvas.bundle.js',
        assetFileNames: 'flows_canvas.[ext]',
      },
    },
  },
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});
