/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        partselectTeal: "#2f6f6b",
        partselectYellow: "#f6c453",
      },
    },
  },
  plugins: [],
};

