import type { Config } from "tailwindcss";

function token(name: string) {
  return `rgb(var(--${name}) / <alpha-value>)`;
}

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
    "../../packages/maps/src/**/*.{ts,tsx}",
    "../../packages/charts/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: token("background"),
        foreground: token("foreground"),
        surface: {
          DEFAULT: token("surface"),
          elevated: token("surface-elevated"),
        },
        "surface-elevated": token("surface-elevated"),
        border: token("border"),
        input: token("border"),
        ring: token("ring"),
        muted: {
          DEFAULT: token("muted"),
          foreground: token("muted-foreground"),
        },
        primary: {
          DEFAULT: token("primary"),
          foreground: token("primary-foreground"),
        },
        info: token("info"),
        success: token("success"),
        warning: token("warning"),
        danger: token("danger"),
        "risk-low": token("risk-low"),
        "risk-watch": token("risk-watch"),
        "risk-medium": token("risk-medium"),
        "risk-high": token("risk-high"),
        "risk-critical": token("risk-critical"),
      },
      borderRadius: {
        lg: "0.625rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      keyframes: {
        "fade-in-0": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-out-0": { from: { opacity: "1" }, to: { opacity: "0" } },
      },
      animation: {
        in: "fade-in-0 150ms ease-out",
        out: "fade-out-0 150ms ease-in",
      },
    },
  },
  plugins: [],
};

export default config;
