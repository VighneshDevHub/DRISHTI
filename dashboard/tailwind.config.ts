import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#FFFFFF",
        panel: "#FAFAFA",
        sider: "#000000",
        border: "#E5E5E5",
        text: "#000000",
        muted: "#737373",
        green: "#10B981",
        amber: "#F59E0B",
        red: "#EF4444",
        blue: "#000000",
        violet: "#000000"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(15, 23, 42, 0.15)"
      }
    }
  },
  plugins: []
};

export default config;
