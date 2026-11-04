import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'frontend/editor/index.js'),
      name: 'InactEditor',
      fileName: 'editor.bundle',
      formats: ['iife'],
    },
    outDir: resolve(__dirname, 'static/js'),
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: 'editor.bundle.js',
      },
    },
  },
});
