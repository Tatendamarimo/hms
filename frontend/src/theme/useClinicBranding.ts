import { useQuery } from "@tanstack/react-query";

/** Public branding shape returned by GET /api/v1/clinics/branding/ */
export interface PublicBranding {
  name: string;
  branding: {
    logo_url: string;
    favicon_url: string;
    primary_color: string;
    secondary_color: string;
    tagline: string;
  };
}

/**
 * Fetch branding from the unauthenticated public endpoint. Used on the
 * login page before any session exists. Falls back to neutral HMS defaults
 * when the backend has zero or multiple active clinics.
 */
export function useClinicBranding() {
  return useQuery({
    queryKey: ["clinics", "branding"],
    queryFn: async (): Promise<PublicBranding> => {
      const res = await fetch("/api/v1/clinics/branding/", { credentials: "include" });
      if (!res.ok) {
        return { name: "HMS", branding: { logo_url: "", favicon_url: "", primary_color: "#1e293b", secondary_color: "#047857", tagline: "" } };
      }
      return res.json();
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
