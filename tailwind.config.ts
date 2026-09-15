import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          green: "#0f4f48",
          "green-70": "#3e756f",
          "green-30": "#a8c7c4",
          "green-10": "#e5f0ef",
          "green-dark": "#0a3733",
          red: "#eb2229",
          "red-70": "#f17075",
          "red-10": "#fce8e9",
          "red-dark": "#c41e24",
          teal: "#1a8f87",
          ink: "#0b1a18",
        },
      },
      fontFamily: {
        sans: [
          "Roboto",
          "Gotham",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,26,24,0.06), 0 1px 12px rgba(11,26,24,0.05)",
        popover: "0 12px 32px rgba(11,26,24,0.18)",
      },
      borderRadius: {
        xl2: "14px",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in .25s ease-out",
        "slide-up": "slide-up .3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
