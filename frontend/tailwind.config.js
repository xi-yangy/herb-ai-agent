/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  // 关闭 preflight，避免与 Vant 4 的基础样式重置冲突
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        // 国风草本语义色板
        primary: {
          DEFAULT: '#2D6B4F',
          light: '#35785C',
          dark: '#245840',
        },
        paper: {
          DEFAULT: '#F5F0E8',
          card: '#FAF7F0',
        },
        ink: {
          DEFAULT: '#2A2A2A',
          secondary: '#4A4A4A',
          faint: '#8C8C8C',
        },
        jade: '#4A7C59',
        ochre: '#C08A3E',
        cinnabar: '#C0392B',
        accent: '#A9663F',
        danger: '#C0392B',
        warning: '#C08A3E',
      },
      fontFamily: {
        sans: ['PingFang SC', 'Helvetica Neue', 'Arial', 'sans-serif'],
        serif: ['"Noto Serif SC"', 'SimSun', 'Songti SC', 'serif'],
      },
      maxWidth: {
        content: '720px',
      },
      screens: {
        mobile: '375px',
        tablet: '768px',
        desktop: '1024px',
      },
    },
  },
  plugins: [],
}
