import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bg:    '#0a0a0c',
        bg2:   '#131318',
        bg3:   '#1c1c24',
        brand: '#ff2d55',
        brand2:'#7c3aed',
        ok:    '#34c759',
        warn:  '#f59e0b',
        err:   '#ff453a',
      },
      backgroundImage: {
        'brand-grad': 'linear-gradient(135deg, #ff2d55 0%, #7c3aed 100%)',
      },
    },
  },
  plugins: [],
}
export default config
