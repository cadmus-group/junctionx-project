"use client";

import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

export interface EChartProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  notMerge?: boolean;
}

export function EChart({ option, height = 280, className, notMerge = true }: EChartProps) {
  const style = useMemo(
    () => ({ height: typeof height === "number" ? `${height}px` : height, width: "100%" }),
    [height]
  );
  return (
    <ReactECharts
      option={option}
      notMerge={notMerge}
      lazyUpdate
      style={style}
      className={className}
      opts={{ renderer: "canvas" }}
    />
  );
}
