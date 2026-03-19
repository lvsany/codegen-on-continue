import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'prepend-ts-nocheck-for-dist',
      writeBundle(options, bundle) {
        const outDir = options.dir
          ? path.resolve(__dirname, options.dir)
          : path.resolve(__dirname, '../dist/gui');

        for (const item of Object.values(bundle)) {
          if (item.type !== 'chunk' || !item.fileName.endsWith('.js')) {
            continue;
          }

          const outputPath = path.join(outDir, item.fileName);
          if (!fs.existsSync(outputPath)) {
            continue;
          }

          const currentCode = fs.readFileSync(outputPath, 'utf8');
          if (!currentCode.startsWith('// @ts-nocheck')) {
            fs.writeFileSync(outputPath, `// @ts-nocheck\n${currentCode}`, 'utf8');
          }
        }
      }
    }
  ],
  build: {
    outDir: '../dist/gui',
    emptyOutDir: true,
    target: 'es2020',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        format: 'iife',
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
        inlineDynamicImports: true
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  define: {
    'process.env': {}
  }
});
