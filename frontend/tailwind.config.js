/** @type {import('tailwindcss').Config} */
// NOTE: Tailwind v4 reads design tokens from CSS @theme in src/index.css
// This file is kept for content path scanning compatibility
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
}
