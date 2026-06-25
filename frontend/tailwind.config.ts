import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        panel: "#101a2d",
        gold: "#d4af37",
        mint: "#49dca2"
      },
      boxShadow: {
        premium: "0 24px 80px rgba(0, 0, 0, 0.36)"
      }
    }
  },
  plugins: []
};

export default config;
