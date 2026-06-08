import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Space Grotesk', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        gmail: ["'Google Sans'", 'Roboto', 'Arial', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
        header: "hsl(var(--header-background))",
        stat: {
          green: "hsl(var(--stat-green))",
          amber: "hsl(var(--stat-amber))",
          blue: "hsl(var(--stat-blue))",
          purple: "hsl(var(--stat-purple))",
        },
        /* ── Gmail / Email-preview UI palette ─────────────────────────────── */
        gmail: {
          bg: "var(--gmail-bg)",
          surface: "var(--gmail-surface)",
          primary: "var(--gmail-text-primary)",
          secondary: "var(--gmail-text-secondary)",
          logo: "var(--gmail-text-logo)",
          border: "var(--gmail-border)",
          /* RGB-channel format enables the /opacity modifier (e.g. /60) */
          hover: "rgb(var(--gmail-hover) / <alpha-value>)",
          "search-hover": "rgb(var(--gmail-search-hover) / <alpha-value>)",
          blue: "var(--gmail-blue)",
          "blue-dark": "var(--gmail-blue-dark)",
          "blue-light": "var(--gmail-blue-light)",
          "search-bg": "var(--gmail-search-bg)",
          "compose-bg": "var(--gmail-compose-bg)",
          "compose-hover": "var(--gmail-compose-hover)",
          "compose-text": "var(--gmail-compose-text)",
          "active-bg": "var(--gmail-active-bg)",
          "active-icon": "var(--gmail-active-icon)",
          "reply-border": "var(--gmail-reply-border)",
        },
        /* ── Content-hint chip (violet palette) ───────────────────────────── */
        "content-hint": {
          border: "hsl(var(--content-hint-border))",
          bg: "hsl(var(--content-hint-bg))",
          text: "hsl(var(--content-hint-text))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
