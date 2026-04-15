/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './code_editor/**/*.{js,jsx,ts,tsx}',
    './html_preview/**/*.{js,jsx,ts,tsx}',
  ],
  corePlugins: {
    container: false, /* We use .app-container for layout - Tailwind's .container applies max-width at breakpoints */
  },
  theme: {
    extend: {},
  },
  plugins: [],
}
