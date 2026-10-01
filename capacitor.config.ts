import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anviqo.industrial',
  appName: 'ANVIQO',
  webDir: 'www',
  server: {
    url: 'https://anviqo.onrender.com',
    cleartext: false,
    androidScheme: 'https'
  }
};

export default config;
