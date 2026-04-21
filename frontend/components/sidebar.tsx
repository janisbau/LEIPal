"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Building2, Globe, Search, Bell, Download, Settings } from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/lous", label: "LOU Explorer", icon: Building2 },
  { href: "/jurisdictions", label: "Jurisdictions", icon: Globe },
  { href: "/search", label: "Company Search", icon: Search },
];

const workspaceItems = [
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/exports", label: "Exports", icon: Download },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-52 bg-card border-r border-edge flex flex-col z-10">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-edge">
        <div className="w-7 h-7 rounded bg-teal flex items-center justify-center text-navy font-bold text-sm">
          L
        </div>
        <div>
          <div className="text-white font-semibold text-sm leading-tight">LEIPal</div>
          <div className="text-muted text-[10px] uppercase tracking-widest">Analytics Terminal</div>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-teal/10 text-teal font-medium"
                : "text-muted hover:text-white hover:bg-white/5"
            )}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}

        <div className="pt-4 pb-1 px-3">
          <span className="text-[10px] uppercase tracking-widest text-muted/60">Workspace</span>
        </div>

        {workspaceItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-teal/10 text-teal font-medium"
                : "text-muted hover:text-white hover:bg-white/5"
            )}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-edge">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-teal animate-pulse" />
          <span className="text-[11px] text-muted">GLEIF · Live</span>
        </div>
      </div>
    </aside>
  );
}
