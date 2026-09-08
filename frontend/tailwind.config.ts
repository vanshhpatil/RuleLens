import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 20px 60px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
