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
        primary: {
          DEFAULT: '#2E7D32',
          light: '#388E3C',
          lighter: '#A5D6A7',
        },
        danger: '#D32F2F',
        warning: '#F57C00',
      },
      maxWidth: {
        content: '1200px',
      },
      screens: {
        mobile: '375px',
        tablet: '768px',
        desktop: '1024px',
      },
      fontFamily: {
        sans: ['PingFang SC', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
