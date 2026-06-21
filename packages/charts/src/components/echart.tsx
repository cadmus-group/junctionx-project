"use client";

import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

export interface EChartProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  notMerge?: boolean;
  /** Text alternative for assistive tech. The canvas is otherwise opaque to it. */
  ariaLabel?: string;
}

export function EChart({ option, height = 280, className, notMerge = true, ariaLabel }: EChartProps) {
  const style = useMemo(
    () => ({ height: typeof height === "number" ? `${height}px` : height, width: "100%" }),
    [height]
  );
  // Enable ECharts' built-in ARIA so it auto-describes the series from the data,
  // unless a chart opts out by setting its own `aria`.
  const accessibleOption = useMemo<EChartsOption>(
    () => ({ aria: { enabled: true }, ...option }),
    [option]
  );
  return (
    <div role="img" aria-label={ariaLabel} className={className}>
      <ReactECharts
        option={accessibleOption}
        notMerge={notMerge}
        lazyUpdate
        style={style}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
}
