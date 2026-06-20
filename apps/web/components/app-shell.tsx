"use client";

import { cn } from "@gridtrace/ui";
import {
  Activity,
  Boxes,
  ClipboardList,
  Database,
  LayoutDashboard,
  type LucideIcon,
  Map as MapIcon,
  Settings,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV: NavItem[] = [
  { href: "/", label: "Command Center", icon: LayoutDashboard },
  { href: "/map", label: "Risk Map", icon: MapIcon },
  { href: "/assets", label: "Assets", icon: Boxes },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/inspections", label: "Inspections", icon: ClipboardList },
  { href: "/analytics", label: "Model Analytics", icon: Activity },
  { href: "/data-quality", label: "Data Quality", icon: Database },
  { href: "/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

// The navigation rail is a fixed near-black monochrome surface in both themes:
// black with white text in light mode, near-black in dark mode.
const RAIL = "bg-[#0A0A0A] dark:bg-[#0D0D0D] text-[#F5F5F2] border-[#2D2D2A]";

function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className={cn("flex w-56 shrink-0 flex-col border-r", RAIL)}>
      <div className="flex h-[52px] items-center gap-2.5 border-b border-[#2D2D2A] px-4">
        <div className="flex h-6 w-6 items-center justify-center rounded-sm border border-white/30">
          <Zap className="h-3.5 w-3.5" />
        </div>
        <span className="text-sm font-semibold tracking-tight">GridTrace</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-sm px-3 py-2 text-[13px] font-medium transition-colors",
                active
                  ? "bg-white text-[#0A0A0A]"
                  : "text-white/60 hover:bg-white/10 hover:text-white"
              )}
              aria-current={active ? "page" : undefined}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

function Topbar({ title }: { title?: string }) {
  return (
    <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-border bg-background px-6">
      <div className="flex items-center gap-2">
        <h1 className="text-sm font-semibold tracking-tight">{title ?? "GridTrace"}</h1>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5 rounded-sm border border-border px-2 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-[#3C8D63]" aria-hidden />
          System nominal
        </span>
        <div className="flex h-7 w-7 items-center justify-center rounded-sm border border-border bg-surface text-[11px] font-semibold text-foreground">
          DO
        </div>
      </div>
    </header>
  );
}

export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const pathname = usePathname();
  const derived = NAV.find((item) => isActive(pathname, item.href))?.label;
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title={title ?? derived} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
