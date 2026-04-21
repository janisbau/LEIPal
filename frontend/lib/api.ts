const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function fetchSummary() {
  const res = await fetch(`${API}/stats/summary`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function fetchGrowth() {
  const res = await fetch(`${API}/stats/growth`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch growth");
  return res.json() as Promise<
    { month: string; new_leis: number; cumulative: number }[]
  >;
}

export async function fetchJurisdictions() {
  const res = await fetch(`${API}/stats/jurisdictions`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch jurisdictions");
  return res.json() as Promise<
    { jurisdiction: string; count: number; share: number }[]
  >;
}

export async function fetchLous() {
  const res = await fetch(`${API}/lous`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch LOUs");
  return res.json() as Promise<
    {
      lou_lei: string;
      lou_name: string;
      country: string;
      status: string;
      total_leis: number;
      active_leis: number;
      inactive_leis: number;
      market_share: number;
    }[]
  >;
}

export async function fetchLou(lei: string) {
  const res = await fetch(`${API}/lous/${lei}`, { cache: "no-store" });
  if (!res.ok) throw new Error("LOU not found");
  return res.json();
}

export async function searchLeis(q: string, limit = 20) {
  const res = await fetch(
    `${API}/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error("Search failed");
  return res.json() as Promise<
    {
      lei: string;
      legal_name: string;
      jurisdiction: string;
      entity_status: string;
      entity_category: string;
      managing_lou: string;
      registration_status: string;
    }[]
  >;
}

export async function fetchLei(lei: string) {
  const res = await fetch(`${API}/search/lei/${lei}`, { cache: "no-store" });
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return n.toString();
}
