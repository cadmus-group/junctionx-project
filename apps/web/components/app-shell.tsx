"use client";

import { cn } from "@gridtrace/ui";
import {
  Activity,
  Boxes,
  ClipboardList,
  Database,
  Gauge,
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

function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Zap className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold tracking-tight">GridTrace</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              aria-current={active ? "page" : undefined}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Gauge className="h-3.5 w-3.5" />
          Demo environment
        </div>
      </div>
    </aside>
  );
}

function Topbar({ title }: { title?: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div>
        <h1 className="text-sm font-semibold">{title ?? "GridTrace"}</h1>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="rounded-full border border-border px-2 py-0.5">Netherlands · EUR</span>
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-foreground">
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
