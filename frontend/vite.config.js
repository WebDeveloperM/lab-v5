import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const readSharedEnv = () => {
  // URL konfiguratsiyasi markaziy ../.env da (frontend/.env ning o'z izohiga qarang), shuning
  // uchun u BAZA, frontend/.env esa faqat ustidan yozadi. Ilgari bu yerda faqat birinchi mavjud
  // fayl o'qilardi — frontend/.env esa doim mavjud (ichida faqat COMPOSE_PROJECT_NAME), shu
  // sababli markaziy ../.env hech qachon o'qilmay, hamma URL pastdagi literal qiymatlarga
  // tushib ketardi. Docker prod build'ida kontekst faqat frontend/ bo'lgani uchun ../.env
  // yo'q — u yerda literal qiymatlar yagona manba, ularni ../.env bilan mos tuting.
  const envCandidates = [
    path.resolve(__dirname, '../.env'),
    path.resolve(__dirname, '.env'),
  ];
  const envPaths = envCandidates.filter((candidate) => fs.existsSync(candidate));
  if (envPaths.length === 0) {
    return {};
  }

  return envPaths
    .map((envPath) => fs.readFileSync(envPath, 'utf-8'))
    .join('\n')
    .split(/\r?\n/)
    .reduce((accumulator, rawLine) => {
      const line = rawLine.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) {
        return accumulator;
      }

      const [key, ...valueParts] = line.split('=');
      accumulator[key.trim()] = valueParts.join('=').trim().replace(/^['"]|['"]$/g, '');
      return accumulator;
    }, {});
};

const sharedEnv = readSharedEnv();
const publicBaseUrl = String(sharedEnv.PUBLIC_BASE_URL || 'https://192.168.101.23').trim().replace(/\/+$/, '');
const backendPort = String(sharedEnv.BACKEND_PORT || '8030').trim();
const frontendPort = String(sharedEnv.FRONTEND_PORT || '6030').trim();
const backendTarget = String(
  sharedEnv.BACKEND_INTERNAL_URL || `http://backend:8030`
).trim().replace(/\/+$/, '');
const frontendPublicUrl = `${publicBaseUrl}:${frontendPort}`;

const employeeServicePublicUrl = String(
  sharedEnv.EMPLOYEE_SERVICE_PUBLIC_URL || 'https://192.168.101.6:5000'
).trim().replace(/\/+$/, '');
const bnpzIdClientId = String(sharedEnv.BNPZID_CLIENT_ID || 'base-laboratory').trim() || 'base-laboratory';
const backendApiUrl = `${frontendPublicUrl}/api/v1`;

const frontendCertPath = path.resolve(__dirname, 'certs/frontend.crt');
const frontendKeyPath = path.resolve(__dirname, 'certs/frontend.key');
const hasFrontendHttpsCerts = fs.existsSync(frontendCertPath) && fs.existsSync(frontendKeyPath);

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_BACKEND_API_URL': JSON.stringify(backendApiUrl),
    'import.meta.env.VITE_EMPLOYEE_SERVICE_WEB_URL': JSON.stringify(employeeServicePublicUrl),
    'import.meta.env.VITE_FRONTEND_PUBLIC_URL': JSON.stringify(frontendPublicUrl),
    'import.meta.env.VITE_BNPZID_CLIENT_ID': JSON.stringify(bnpzIdClientId),
  },
  server: {
    port: Number(frontendPort) || 6030,
    host: '0.0.0.0',
    https: hasFrontendHttpsCerts
      ? {
          cert: fs.readFileSync(frontendCertPath),
          key: fs.readFileSync(frontendKeyPath),
        }
      : false,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        secure: false,
      },
      '/media': {
        target: backendTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: false,
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('pdfmake')) return 'vendor-pdfmake';
            if (id.includes('xlsx')) return 'vendor-xlsx';
            return 'vendor';
          }
        },
      },
    },
  },
});
