import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta base neutra; a identidade visual definitiva entra no Bloco 9.
        primary: {
          DEFAULT: 'hsl(220 70% 35%)',
          foreground: 'hsl(0 0% 100%)',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
