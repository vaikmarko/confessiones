/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.jsx",
    "./public/**/*.html",
    "./public/js/**/*.jsx",
    "./public/static/js/**/*.jsx"
  ],
  theme: {
    extend: {
      colors: {
        purple: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#8639E8',
          700: '#7c3aed',
          800: '#6b21a8',
          900: '#581c87',
        }
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms')
  ]
} 