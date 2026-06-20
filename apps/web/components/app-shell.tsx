"use client";

import {
  cn,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@gridtrace/ui";
import {
  Activity,
  Boxes,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  LogOut,
  type LucideIcon,
  Map as MapIcon,
  Settings,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS, type Role } from "@/lib/roles";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Roles allowed to see this entry. The shell is identical across roles; only
   *  the available sections differ. */
  roles: Role[];
  /** Kept for title derivation but not rendered in the sidebar (e.g. Settings,
   *  which now lives in the profile menu). */
  hidden?: boolean;
}

const ALL: Role[] = ["admin", "analyst", "inspector"];

const NAV: NavItem[] = [
  { href: "/", label: "Command Center", icon: LayoutDashboard, roles: ALL },
  { href: "/map", label: "Risk Map", icon: MapIcon, roles: ALL },
  { href: "/assets", label: "Assets", icon: Boxes, roles: ["admin", "analyst"] },
  { href: "/customers", label: "Customers", icon: Users, roles: ALL },
  { href: "/inspections", label: "Inspections", icon: ClipboardList, roles: ["admin", "inspector"] },
  { href: "/analytics", label: "Model Analytics", icon: Activity, roles: ["admin", "analyst"] },
  { href: "/data-quality", label: "Data Quality", icon: Database, roles: ["admin", "analyst"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ALL, hidden: true },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  if (!first) return "—";
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const last = parts[parts.length - 1] ?? first;
  return ((first[0] ?? "") + (last[0] ?? "")).toUpperCase();
}

// The navigation rail is a fixed near-black monochrome surface in both themes:
// black with white text in light mode, near-black in dark mode.
const RAIL = "bg-[#0A0A0A] dark:bg-[#0D0D0D] text-[#F5F5F2] border-[#2D2D2A]";

function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const role = user?.role ?? "analyst";
  const items = NAV.filter((item) => !item.hidden && item.roles.includes(role));

  return (
    <aside className={cn("flex w-56 shrink-0 flex-col border-r", RAIL)}>
      <div className="flex h-[52px] items-center gap-2.5 border-b border-[#2D2D2A] px-4">
        <div className="flex h-6 w-6 items-center justify-center rounded-sm border border-white/30">
          <Zap className="h-3.5 w-3.5" />
        </div>
        <span className="text-sm font-semibold tracking-tight">GridTrace</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {items.map((item) => {
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
      <div className="space-y-2 border-t border-[#2D2D2A] p-3 text-[11px] text-white/55">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-[#3C8D63]" aria-hidden />
          <span className="flex items-center gap-1.5">
            <Gauge className="h-3.5 w-3.5" />
            Demo environment
          </span>
        </div>
      </div>
    </aside>
  );
}

function ProfileMenu() {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Open profile menu"
          className="flex h-7 w-7 items-center justify-center rounded-sm bg-muted text-[11px] font-semibold text-foreground transition-colors hover:bg-surface-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {initials(user.name)}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-foreground">{user.name}</span>
          <span className="text-xs font-normal text-muted-foreground">{ROLE_LABELS[user.role]}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <Settings className="h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => logout()}>
          <LogOut className="h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
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
        <ProfileMenu />
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
