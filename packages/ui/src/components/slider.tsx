"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export interface SliderProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "onChange"> {
  value: number;
  onValueChange?: (value: number) => void;
}

export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value, onValueChange, min = 0, max = 100, step = 1, ...props }, ref) => (
    <input
      ref={ref}
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onValueChange?.(Number(e.target.value))}
      className={cn(
        "h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary",
        className
      )}
      {...props}
    />
  )
);
Slider.displayName = "Slider";
