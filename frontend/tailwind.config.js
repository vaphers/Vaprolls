/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sf: {
          header: '#FFE08A',
          headerHover: '#FFD76A',
          border: '#C8B670',
          borderLight: '#E2D5A0',
          bgLight: '#FFF7D6',
          bgActive: '#FFE08A',
          accent: '#15803D',
          warning: '#B45309',
          danger: '#B91C1C',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}

