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
          DEFAULT: '#2F5D46',
          light: '#3A6B50',
          dark: '#1F3D2E',
        },
        paper: {
          DEFAULT: '#F7F3EA',
          card: '#FFFDF7',
        },
        ink: {
          DEFAULT: '#2A2A28',
          secondary: '#6B6B63',
          faint: '#A8A39A',
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
