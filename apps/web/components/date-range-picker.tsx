"use client";

import { Input, Label } from "@gridtrace/ui";

function toDateInput(iso?: string): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

function toIso(date: string): string | undefined {
  if (!date) return undefined;
  return new Date(`${date}T00:00:00.000Z`).toISOString();
}

export interface DateRangePickerProps {
  from?: string;
  to?: string;
  onChange: (range: { from?: string; to?: string }) => void;
}

export function DateRangePicker({ from, to, onChange }: DateRangePickerProps) {
  return (
    <div className="flex items-end gap-2">
      <div className="space-y-1">
        <Label htmlFor="date-from" className="text-xs text-muted-foreground">
          From
        </Label>
        <Input
          id="date-from"
          type="date"
          className="h-8 w-[9.5rem]"
          value={toDateInput(from)}
          onChange={(e) => onChange({ from: toIso(e.target.value), to })}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="date-to" className="text-xs text-muted-foreground">
          To
        </Label>
        <Input
          id="date-to"
          type="date"
          className="h-8 w-[9.5rem]"
          value={toDateInput(to)}
          onChange={(e) => onChange({ from, to: toIso(e.target.value) })}
        />
      </div>
    </div>
  );
}
