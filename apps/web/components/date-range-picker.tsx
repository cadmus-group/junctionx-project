"use client";

import { cn, Label } from "@gridtrace/ui";
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  addDays,
  addMonths,
  buildGrid,
  fmtShort,
  MONTHS,
  parseIso,
  sameDay,
  startOfMonth,
  todayUtc,
  WEEKDAYS,
} from "./calendar-utils";

export interface DateRangePickerProps {
  from?: string;
  to?: string;
  onChange: (range: { from?: string; to?: string }) => void;
}

type Mode = "range" | "day";

export function DateRangePicker({ from, to, onChange }: DateRangePickerProps) {
  const fromDay = useMemo(() => parseIso(from), [from]);
  const toDay = useMemo(() => parseIso(to), [to]);
  const isSingle = sameDay(fromDay, toDay);

  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>(() => (fromDay && isSingle ? "day" : "range"));
  const [view, setView] = useState<Date>(() => startOfMonth(fromDay ?? todayUtc()));
  const rootRef = useRef<HTMLDivElement>(null);

  // Keep the visible month in sync when an external range arrives.
  useEffect(() => {
    if (fromDay) setView(startOfMonth(fromDay));
  }, [fromDay]);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function selectDay(day: Date) {
    // Single-day mode: one click picks exactly that day.
    if (mode === "day") {
      onChange({ from: day.toISOString(), to: day.toISOString() });
      setOpen(false);
      return;
    }
    // Range mode — no anchor yet, or a complete range exists → start fresh.
    if (!fromDay || (fromDay && toDay)) {
      onChange({ from: day.toISOString(), to: undefined });
      return;
    }
    // Anchor set, pick the other end (auto-order).
    if (day.getTime() < fromDay.getTime()) {
      onChange({ from: day.toISOString(), to: fromDay.toISOString() });
    } else {
      onChange({ from: fromDay.toISOString(), to: day.toISOString() });
    }
    setOpen(false);
  }

  function applyToday() {
    const t = todayUtc();
    onChange({ from: t.toISOString(), to: t.toISOString() });
    setView(startOfMonth(t));
    setOpen(false);
  }

  function applyPreset(days: number) {
    const end = todayUtc();
    const start = addDays(end, -(days - 1));
    onChange({ from: start.toISOString(), to: end.toISOString() });
    setView(startOfMonth(end));
    setOpen(false);
  }

  function clear() {
    onChange({ from: undefined, to: undefined });
  }

  const grid = useMemo(() => buildGrid(view), [view]);
  const today = todayUtc();

  const triggerLabel = fromDay
    ? toDay
      ? isSingle
        ? fmtShort(fromDay)
        : `${fmtShort(fromDay)} – ${fmtShort(toDay)}`
      : `${fmtShort(fromDay)} – …`
    : "Any dates";

  return (
    <div className="space-y-1" ref={rootRef}>
      <Label className="text-xs text-muted-foreground">Date range</Label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="dialog"
          aria-expanded={open}
          className={cn(
            "flex h-8 w-[13rem] items-center gap-2 rounded-sm border border-border bg-surface px-2.5 text-left text-sm text-foreground shadow-sm transition-colors hover:border-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            open && "ring-2 ring-ring"
          )}
        >
          <CalendarDays className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className={cn("flex-1 truncate tabular-nums", !fromDay && "text-muted-foreground")}>
            {triggerLabel}
          </span>
          {fromDay ? (
            <span
              role="button"
              tabIndex={0}
              aria-label="Clear date range"
              onClick={(e) => {
                e.stopPropagation();
                clear();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  clear();
                }
              }}
              className="rounded-sm p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          ) : null}
        </button>

        {open ? (
          <div
            role="dialog"
            aria-label="Choose a date range"
            className="absolute left-0 top-[calc(100%+0.375rem)] z-50 w-64 rounded-md border border-border bg-surface-elevated p-3 shadow-lg animate-in"
          >
            {/* Mode toggle: single day vs range */}
            <div className="mb-3 grid grid-cols-2 gap-0.5 rounded-sm border border-border p-0.5">
              {(["day", "range"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded-sm px-2 py-1 text-xs font-medium capitalize transition-colors",
                    mode === m
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {m === "day" ? "Single day" : "Range"}
                </button>
              ))}
            </div>

            {/* Month navigation */}
            <div className="mb-2 flex items-center justify-between">
              <button
                type="button"
                aria-label="Previous month"
                onClick={() => setView((v) => addMonths(v, -1))}
                className="flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm font-semibold tracking-tight">
                {MONTHS[view.getUTCMonth()]} {view.getUTCFullYear()}
              </span>
              <button
                type="button"
                aria-label="Next month"
                onClick={() => setView((v) => addMonths(v, 1))}
                className="flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Weekday header */}
            <div className="grid grid-cols-7 gap-0.5 pb-1">
              {WEEKDAYS.map((w) => (
                <div
                  key={w}
                  className="flex h-6 items-center justify-center text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
                >
                  {w}
                </div>
              ))}
            </div>

            {/* Day grid */}
            <div className="grid grid-cols-7 gap-0.5">
              {grid.map((day) => {
                const outside = day.getUTCMonth() !== view.getUTCMonth();
                const isStart = sameDay(day, fromDay);
                const isEnd = sameDay(day, toDay);
                const isEndpoint = isStart || isEnd;
                const inRange =
                  !!fromDay &&
                  !!toDay &&
                  day.getTime() > fromDay.getTime() &&
                  day.getTime() < toDay.getTime();
                const isToday = sameDay(day, today);
                return (
                  <button
                    key={day.toISOString()}
                    type="button"
                    onClick={() => selectDay(day)}
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-sm text-xs tabular-nums transition-colors",
                      !isEndpoint && !inRange && "text-foreground hover:bg-muted",
                      outside && !isEndpoint && !inRange && "text-muted-foreground/40",
                      inRange && "bg-muted text-foreground",
                      isEndpoint && "bg-foreground font-semibold text-background",
                      isToday && !isEndpoint && "ring-1 ring-inset ring-border"
                    )}
                  >
                    {day.getUTCDate()}
                  </button>
                );
              })}
            </div>

            {/* Presets */}
            <div className="mt-3 flex items-center gap-1.5 border-t border-border pt-2.5">
              {mode === "day" ? (
                <button
                  type="button"
                  onClick={applyToday}
                  className="rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
                >
                  Today
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => applyPreset(7)}
                    className="rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
                  >
                    7 days
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset(30)}
                    className="rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
                  >
                    30 days
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={clear}
                className="ml-auto rounded-sm px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                Clear
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
