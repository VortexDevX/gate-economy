/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f7fbf9",
          100: "#e4f3ef",
          200: "#bfe3dc",
          300: "#8fd0c7",
          400: "#00a9b4",
          500: "#007d86",
          600: "#a16900",
          700: "#805300",
          800: "#523600",
          900: "#172522",
        },
      },
    },
  },
  plugins: [],
};
