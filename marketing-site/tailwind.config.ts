import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#2563EB",
          600: "#2340C8",
          700: "#1E40AF",
          800: "#1E3A8A",
          900: "#172554",
        },
        accent: {
          DEFAULT: "#14B8D4",
          dark: "#0E7490",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F8FAFC",
          border: "#E2E8F0",
        },
        ink: {
          DEFAULT: "#0F172A",
          muted: "#64748B",
          faint: "#94A3B8",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 12px 35px rgba(15, 23, 42, 0.08)",
        glow: "0 0 60px rgba(37, 99, 235, 0.15)",
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "slide-up": "slideUp 0.6s ease-out forwards",
        float: "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      backgroundImage: {
        "hero-gradient":
          "linear-gradient(135deg, #2340C8 0%, #2563EB 50%, #14B8D4 100%)",
        "mesh-gradient":
          "radial-gradient(at 40% 20%, rgba(37, 99, 235, 0.12) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(20, 184, 212, 0.1) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(35, 64, 200, 0.08) 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
};

export default config;
