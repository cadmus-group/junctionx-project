"use client";

import { cn } from "@gridtrace/ui";
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  addMonths,
  buildGrid,
  fmtFull,
  MONTHS,
  parseIso,
  sameDay,
  startOfMonth,
  toDateValue,
  todayUtc,
  WEEKDAYS,
} from "./calendar-utils";

export interface DatePickerProps {
  /** Selected date as a YYYY-MM-DD value (or undefined when empty). */
  value?: string;
  onChange: (value?: string) => void;
  id?: string;
  placeholder?: string;
}

/** Single-day picker sharing the calendar styling with DateRangePicker. */
export function DatePicker({ value, onChange, id, placeholder = "Pick a date" }: DatePickerProps) {
  const selected = useMemo(() => parseIso(value), [value]);

  const [open, setOpen] = useState(false);
  const [view, setView] = useState<Date>(() => startOfMonth(selected ?? todayUtc()));
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selected) setView(startOfMonth(selected));
  }, [selected]);

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
    onChange(toDateValue(day));
    setOpen(false);
  }

  const grid = useMemo(() => buildGrid(view), [view]);
  const today = todayUtc();

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        id={id}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={cn(
          "flex h-9 w-full items-center gap-2 rounded-md border border-border bg-surface px-3 text-left text-sm shadow-sm transition-colors hover:border-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          open && "ring-2 ring-ring"
        )}
      >
        <CalendarDays className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className={cn("flex-1 truncate", selected ? "text-foreground" : "text-muted-foreground")}>
          {selected ? fmtFull(selected) : placeholder}
        </span>
        {selected ? (
          <span
            role="button"
            tabIndex={0}
            aria-label="Clear date"
            onClick={(e) => {
              e.stopPropagation();
              onChange(undefined);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                onChange(undefined);
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
          aria-label="Choose a date"
          className="absolute left-0 top-[calc(100%+0.375rem)] z-50 w-64 rounded-md border border-border bg-surface-elevated p-3 shadow-lg animate-in"
        >
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

          <div className="grid grid-cols-7 gap-0.5">
            {grid.map((day) => {
              const outside = day.getUTCMonth() !== view.getUTCMonth();
              const isSelected = sameDay(day, selected);
              const isToday = sameDay(day, today);
              return (
                <button
                  key={day.toISOString()}
                  type="button"
                  onClick={() => selectDay(day)}
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-sm text-xs tabular-nums transition-colors",
                    !isSelected && "text-foreground hover:bg-muted",
                    outside && !isSelected && "text-muted-foreground/40",
                    isSelected && "bg-foreground font-semibold text-background",
                    isToday && !isSelected && "ring-1 ring-inset ring-border"
                  )}
                >
                  {day.getUTCDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex items-center gap-1.5 border-t border-border pt-2.5">
            <button
              type="button"
              onClick={() => selectDay(today)}
              className="rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => onChange(undefined)}
              className="ml-auto rounded-sm px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              Clear
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
