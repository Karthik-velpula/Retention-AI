/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#132238",
        tide: "#1b4965",
        mist: "#edf6f9",
        coral: "#ff7f51",
        sand: "#f4d35e",
        mint: "#75b798"
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        sans: ["Trebuchet MS", "Verdana", "sans-serif"]
      },
      boxShadow: {
        soft: "0 20px 45px rgba(19, 34, 56, 0.12)"
      }
    }
  },
  plugins: []
};
