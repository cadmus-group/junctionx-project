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
    "./src/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
    "../../packages/maps/src/**/*.{ts,tsx}",
    "../../packages/charts/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: token("background"),
        foreground: {
          DEFAULT: token("foreground"),
          muted: token("foreground-muted"),
          subtle: token("foreground-subtle"),
        },
        surface: {
          DEFAULT: token("surface"),
          subtle: token("surface-subtle"),
          strong: token("surface-strong"),
          elevated: token("surface-elevated"),
        },
        "surface-elevated": token("surface-elevated"),
        border: {
          DEFAULT: token("border"),
          strong: token("border-strong"),
        },
        "grid-line": token("grid-line"),
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
        inverse: {
          DEFAULT: token("inverse"),
          foreground: token("inverse-foreground"),
        },
        // Semantic data colors — meaning, never decoration.
        info: token("information"),
        information: token("information"),
        success: token("positive"),
        positive: token("positive"),
        warning: token("warning"),
        danger: token("negative"),
        negative: token("negative"),
        selected: token("selected"),
        "comparison-series": token("comparison-series"),
        "forecast-series": token("forecast-series"),
        "neutral-series-1": token("neutral-series-1"),
        "neutral-series-2": token("neutral-series-2"),
        "risk-low": token("risk-low"),
        "risk-watch": token("risk-watch"),
        "risk-medium": token("risk-medium"),
        "risk-high": token("risk-high"),
        "risk-critical": token("risk-critical"),
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 1px)",
        sm: "2px",
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
