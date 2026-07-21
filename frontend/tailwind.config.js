/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff8dc",
          100: "#fcecb3",
          200: "#f6da7f",
          300: "#edc557",
          400: "#e5ae38",
          500: "#c98b22",
          600: "#a66718",
          700: "#744515",
          800: "#492c14",
          900: "#291b11",
        },
      },
    },
  },
  plugins: [],
};
