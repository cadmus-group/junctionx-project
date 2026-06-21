import type { EChartsOption } from "echarts";
import type { ChartPalette } from "./palette";
import { DEFAULT_PALETTE, RISK_TIER_SEQUENCE, riskTierColor } from "./palette";
import type {
  LossTrend,
  ModelRegistryEntry,
  PeerComparisonPoint,
  RiskTier,
  TransformerReconciliation,
} from "@gridtrace/contracts";

export { DEFAULT_PALETTE, RISK_TIER_SEQUENCE, riskTierColor };
export type { ChartPalette };

function baseGrid(): EChartsOption["grid"] {
  return { left: 48, right: 24, top: 32, bottom: 36, containLabel: true };
}

function axisLine(palette: ChartPalette) {
  return { lineStyle: { color: palette.border } };
}

function splitLine(palette: ChartPalette) {
  return { lineStyle: { color: palette.grid } };
}

export interface OptionArgs {
  palette?: ChartPalette;
  locale?: string;
}

function shortTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
}

/** Compact y-axis ticks: 150000 → "150k"; small values are left as-is. */
function compactNumber(value: number): string {
  return Math.abs(value) >= 1000 ? `${value / 1000}k` : `${value}`;
}

export function buildLossTrendOption(
  trend: LossTrend,
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  const x = trend.points.map((p) => shortTime(p.timestamp));
  return {
    color: [palette.foreground, palette.neutral1, palette.warning, palette.danger],
    grid: baseGrid(),
    tooltip: { trigger: "axis" },
    legend: { textStyle: { color: palette.muted }, top: 0 },
    xAxis: {
      type: "category",
      data: x,
      axisLine: axisLine(palette),
      axisLabel: { color: palette.muted },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: palette.muted, formatter: compactNumber },
      splitLine: splitLine(palette),
    },
    series: [
      {
        name: "Energy input",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: trend.points.map((p) => p.energy_input_kwh),
      },
      {
        name: "Metered output",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: trend.points.map((p) => p.metered_output_kwh),
      },
      {
        name: "Technical loss",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: trend.points.map((p) => p.technical_loss_kwh),
      },
      {
        name: "Unexplained loss",
        type: "line",
        smooth: true,
        areaStyle: { opacity: 0.15 },
        showSymbol: false,
        data: trend.points.map((p) => p.unexplained_loss_kwh),
      },
    ],
  };
}

export interface TimeSeriesSeries {
  name: string;
  data: number[];
  color?: string;
  area?: boolean;
  dashed?: boolean;
}

export function buildTimeSeriesOption(
  categories: string[],
  series: TimeSeriesSeries[],
  { palette = DEFAULT_PALETTE, unit = "kWh" }: OptionArgs & { unit?: string } = {}
): EChartsOption {
  return {
    color: series.map((s, i) => {
      const fallback = [palette.foreground, palette.comparison, palette.warning];
      return s.color ?? fallback[i % fallback.length] ?? palette.foreground;
    }),
    grid: baseGrid(),
    tooltip: { trigger: "axis" },
    legend: { textStyle: { color: palette.muted }, top: 0 },
    xAxis: {
      type: "category",
      data: categories,
      axisLine: axisLine(palette),
      axisLabel: { color: palette.muted },
    },
    yAxis: {
      type: "value",
      name: unit,
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      splitLine: splitLine(palette),
    },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      smooth: true,
      showSymbol: false,
      lineStyle: s.dashed ? { type: "dashed", width: 1.5 } : { width: 2 },
      areaStyle: s.area ? { opacity: 0.12 } : undefined,
      data: s.data,
    })),
  };
}

export function buildActualVsExpectedOption(
  points: PeerComparisonPoint[],
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  return buildTimeSeriesOption(
    points.map((p) => shortTime(p.timestamp)),
    [
      { name: "Actual", data: points.map((p) => p.customer_kwh), color: palette.foreground },
      {
        name: "Expected",
        data: points.map((p) => p.expected_kwh),
        color: palette.comparison,
        dashed: true,
        area: true,
      },
    ],
    { palette }
  );
}

export function buildPeerComparisonOption(
  points: PeerComparisonPoint[],
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  return buildTimeSeriesOption(
    points.map((p) => shortTime(p.timestamp)),
    [
      { name: "This customer", data: points.map((p) => p.customer_kwh), color: palette.foreground },
      {
        name: "Peer median",
        data: points.map((p) => p.peer_median_kwh),
        color: palette.neutral2,
        dashed: true,
      },
    ],
    { palette }
  );
}

export function buildEnergyWaterfallOption(
  reconciliation: Pick<TransformerReconciliation, "waterfall">,
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  const steps = reconciliation.waterfall;
  const labels = steps.map((s) => s.label);

  const base: number[] = [];
  const visible: number[] = [];
  let running = 0;
  for (const step of steps) {
    if (step.kind === "input" || step.kind === "residual") {
      base.push(0);
      visible.push(step.value);
      running = step.value;
    } else {
      running = running - step.value;
      base.push(running);
      visible.push(step.value);
    }
  }

  const colorFor = (kind: string): string =>
    kind === "input" ? palette.foreground : kind === "residual" ? palette.danger : palette.neutral1;

  return {
    grid: baseGrid(),
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: axisLine(palette),
      axisLabel: { color: palette.muted, interval: 0 },
    },
    yAxis: {
      type: "value",
      name: "kWh",
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      splitLine: splitLine(palette),
    },
    series: [
      {
        type: "bar",
        stack: "wf",
        itemStyle: { color: "transparent" },
        emphasis: { itemStyle: { color: "transparent" } },
        data: base,
        silent: true,
      },
      {
        type: "bar",
        stack: "wf",
        data: steps.map((s) => ({ value: visible[steps.indexOf(s)], itemStyle: { color: colorFor(s.kind) } })),
        label: { show: true, position: "top", color: palette.foreground },
      },
    ],
  };
}

export function buildRiskDistributionOption(
  breakdown: { tier: RiskTier; count: number }[],
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  const ordered = RISK_TIER_SEQUENCE.map((tier) => ({
    tier,
    count: breakdown.find((b) => b.tier === tier)?.count ?? 0,
  }));
  return {
    grid: baseGrid(),
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: ordered.map((o) => o.tier),
      axisLine: axisLine(palette),
      axisLabel: { color: palette.muted },
    },
    yAxis: {
      type: "value",
      name: "metering points",
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      splitLine: splitLine(palette),
    },
    series: [
      {
        type: "bar",
        data: ordered.map((o) => ({
          value: o.count,
          itemStyle: { color: riskTierColor(o.tier, palette) },
        })),
        barWidth: "55%",
      },
    ],
  };
}

export interface PrecisionRecallPoint {
  recall: number;
  precision: number;
}

export function buildPrecisionRecallOption(
  points: PrecisionRecallPoint[],
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  return {
    grid: baseGrid(),
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "value",
      name: "Recall",
      min: 0,
      max: 1,
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      axisLine: axisLine(palette),
      splitLine: splitLine(palette),
    },
    yAxis: {
      type: "value",
      name: "Precision",
      min: 0,
      max: 1,
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      splitLine: splitLine(palette),
    },
    series: [
      {
        type: "line",
        smooth: true,
        showSymbol: false,
        color: palette.info,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.1 },
        data: points.map((p) => [p.recall, p.precision]),
      },
    ],
  };
}

export interface CalibrationPoint {
  predicted: number;
  observed: number;
}

export function buildCalibrationOption(
  points: CalibrationPoint[],
  { palette = DEFAULT_PALETTE }: OptionArgs = {}
): EChartsOption {
  return {
    grid: baseGrid(),
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "value",
      name: "Predicted",
      min: 0,
      max: 1,
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      axisLine: axisLine(palette),
      splitLine: splitLine(palette),
    },
    yAxis: {
      type: "value",
      name: "Observed",
      min: 0,
      max: 1,
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      splitLine: splitLine(palette),
    },
    series: [
      {
        name: "Perfect calibration",
        type: "line",
        showSymbol: false,
        lineStyle: { type: "dashed", color: palette.muted },
        data: [
          [0, 0],
          [1, 1],
        ],
      },
      {
        name: "Model",
        type: "line",
        smooth: true,
        color: palette.info,
        data: points.map((p) => [p.predicted, p.observed]),
      },
    ],
  };
}

export function precisionRecallFromModel(entry: ModelRegistryEntry): PrecisionRecallPoint[] {
  const anchor = Math.min(0.99, Math.max(0.05, entry.metrics.precision_at_k));
  const steps = 11;
  return Array.from({ length: steps }, (_, i) => {
    const recall = i / (steps - 1);
    const precision = Math.max(0.05, anchor * (1 - 0.55 * recall));
    return { recall, precision };
  });
}
