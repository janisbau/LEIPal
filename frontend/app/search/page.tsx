"use client";

import { useState, useTransition, useRef } from "react";
import { Search } from "lucide-react";
import { searchLeis } from "@/lib/api";
import Link from "next/link";
import { clsx } from "clsx";

type Result = {
  lei: string;
  legal_name: string;
  jurisdiction: string;
  entity_status: string;
  entity_category: string;
  managing_lou: string;
  managing_lou_name: string | null;
  registration_status: string;
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[] | null>(null);
  const [isPending, startTransition] = useTransition();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleChange(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 2) {
      setResults(null);
      return;
    }
    debounceRef.current = setTimeout(() => {
      startTransition(async () => {
        try {
          const data = await searchLeis(value.trim());
          setResults(data);
        } catch {
          setResults([]);
        }
      });
    }, 300);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">Company Search</h1>
        <p className="text-xs text-muted mt-0.5">
          Search 3.16M entities by name or LEI code
        </p>
      </div>

      {/* Search input */}
      <div className="relative">
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Enter company name or LEI code…"
          className="w-full bg-card border border-edge rounded-lg pl-9 pr-4 py-3 text-sm text-white placeholder:text-muted focus:outline-none focus:border-teal transition-colors"
        />
        {isPending && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-teal border-t-transparent animate-spin" />
        )}
      </div>

      {/* Results */}
      {results === null && (
        <p className="text-sm text-muted text-center py-12">
          Type at least 2 characters to search
        </p>
      )}

      {results !== null && results.length === 0 && (
        <p className="text-sm text-muted text-center py-12">
          No results for &ldquo;{query}&rdquo;
        </p>
      )}

      {results !== null && results.length > 0 && (
        <div className="bg-card border border-edge rounded-lg overflow-hidden">
          <div className="px-4 py-2 border-b border-edge">
            <span className="text-xs text-muted">
              {results.length} result{results.length !== 1 ? "s" : ""}
              {results.length === 20 ? " (showing top 20)" : ""}
            </span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-left">
                <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                  Entity
                </th>
                <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                  Jurisdiction
                </th>
                <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                  Managing LOU
                </th>
                <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr
                  key={r.lei}
                  className="border-b border-edge/50 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link href={`/lei/${r.lei}`} className="group flex flex-col">
                      <span className="text-white group-hover:text-teal transition-colors font-medium">
                        {r.legal_name || "—"}
                      </span>
                      <span className="text-[11px] text-muted font-mono">
                        {r.lei}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted text-xs">
                    {r.jurisdiction || "—"}
                  </td>
                  <td className="px-4 py-3 text-muted text-xs">
                    {r.managing_lou_name || r.managing_lou || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        "text-[11px] font-medium px-2 py-0.5 rounded uppercase tracking-wider",
                        r.entity_status === "ACTIVE"
                          ? "bg-teal/10 text-teal"
                          : "bg-danger/10 text-danger"
                      )}
                    >
                      {r.entity_status || "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
