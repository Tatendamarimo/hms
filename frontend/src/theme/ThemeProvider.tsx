import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";
import type { Clinic } from "../api/types";
import { useClinicBranding, type PublicBranding } from "./useClinicBranding";

interface ThemeContextValue {
  clinicName: string;
  logoUrl: string;
  faviconUrl: string;
  primaryColor: string;
  secondaryColor: string;
  tagline: string;
}

const DEFAULT_THEME: ThemeContextValue = {
  clinicName: "HMS",
  logoUrl: "",
  faviconUrl: "",
  primaryColor: "#1e293b",
  secondaryColor: "#047857",
  tagline: "",
};

const ThemeContext = createContext<ThemeContextValue>(DEFAULT_THEME);

/**
 * Parse a hex color into r, g, b for CSS rgba() usage.
 */
function hexToRgb(hex: string): string {
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  if (isNaN(num)) return "30, 41, 59";
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `${r}, ${g}, ${b}`;
}

/**
 * Lighten a hex color by mixing with white (for hover/light variants).
 */
function lightenHex(hex: string, amount: number): string {
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  if (isNaN(num)) return hex;
  const r = Math.min(255, ((num >> 16) & 255) + Math.round(255 * amount));
  const g = Math.min(255, ((num >> 8) & 255) + Math.round(255 * amount));
  const b = Math.min(255, (num & 255) + Math.round(255 * amount));
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

/**
 * Apply branding to CSS custom properties on :root.
 */
function applyTheme(primary: string, secondary: string) {
  const root = document.documentElement;
  root.style.setProperty("--hms-primary", primary);
  root.style.setProperty("--hms-primary-hover", lightenHex(primary, 0.1));
  root.style.setProperty("--hms-primary-light", lightenHex(primary, 0.85));
  root.style.setProperty("--hms-primary-rgb", hexToRgb(primary));

  root.style.setProperty("--hms-secondary", secondary);
  root.style.setProperty("--hms-secondary-hover", lightenHex(secondary, 0.1));
  root.style.setProperty("--hms-secondary-light", lightenHex(secondary, 0.85));
  root.style.setProperty("--hms-secondary-rgb", hexToRgb(secondary));
}

/**
 * Apply favicon dynamically.
 */
function applyFavicon(url: string) {
  if (!url) return;
  let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    document.head.appendChild(link);
  }
  link.href = url;
}

export function ThemeProvider({
  /** When a user is logged in, pass their active clinic for richer branding */
  activeClinic,
  children,
}: {
  activeClinic?: Clinic | null;
  children: ReactNode;
}) {
  // Fetch public branding (used before login and as fallback)
  const publicBranding = useClinicBranding();

  const theme = useMemo<ThemeContextValue>(() => {
    // Prefer the logged-in user's active clinic branding (richer data)
    if (activeClinic) {
      // The clinic object from /auth/me/ includes branding if the serializer sends it
      const branding = (activeClinic as Clinic & { branding?: PublicBranding["branding"] }).branding;
      return {
        clinicName: activeClinic.name,
        logoUrl: branding?.logo_url ?? "",
        faviconUrl: branding?.favicon_url ?? "",
        primaryColor: branding?.primary_color ?? DEFAULT_THEME.primaryColor,
        secondaryColor: branding?.secondary_color ?? DEFAULT_THEME.secondaryColor,
        tagline: branding?.tagline ?? "",
      };
    }

    // Use public branding (login page, no session)
    if (publicBranding.data) {
      return {
        clinicName: publicBranding.data.name,
        logoUrl: publicBranding.data.branding.logo_url,
        faviconUrl: publicBranding.data.branding.favicon_url,
        primaryColor: publicBranding.data.branding.primary_color,
        secondaryColor: publicBranding.data.branding.secondary_color,
        tagline: publicBranding.data.branding.tagline,
      };
    }

    return DEFAULT_THEME;
  }, [activeClinic, publicBranding.data]);

  // Apply CSS variables whenever theme changes
  useEffect(() => {
    applyTheme(theme.primaryColor, theme.secondaryColor);
  }, [theme.primaryColor, theme.secondaryColor]);

  // Update document title
  useEffect(() => {
    document.title = theme.clinicName === "HMS" ? "HMS" : `${theme.clinicName} — HMS`;
  }, [theme.clinicName]);

  // Apply favicon
  useEffect(() => {
    applyFavicon(theme.faviconUrl);
  }, [theme.faviconUrl]);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
