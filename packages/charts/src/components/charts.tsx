"use client";

import type {
  LossTrend,
  PeerComparisonPoint,
  RiskTier,
  TransformerReconciliation,
} from "@gridtrace/contracts";
import { EChart } from "./echart";
import {
  buildActualVsExpectedOption,
  buildCalibrationOption,
  buildEnergyWaterfallOption,
  buildLossTrendOption,
  buildPeerComparisonOption,
  buildPrecisionRecallOption,
  buildRiskDistributionOption,
  buildTimeSeriesOption,
  type CalibrationPoint,
  type ChartPalette,
  type PrecisionRecallPoint,
  type TimeSeriesSeries,
} from "../options";

export interface BaseChartProps {
  height?: number | string;
  className?: string;
  palette?: ChartPalette;
  /** Text alternative for assistive tech (forwarded to the chart's role="img" wrapper). */
  ariaLabel?: string;
}

export function TimeSeriesChart({
  categories,
  series,
  unit,
  palette,
  ...rest
}: BaseChartProps & {
  categories: string[];
  series: TimeSeriesSeries[];
  unit?: string;
}) {
  return <EChart option={buildTimeSeriesOption(categories, series, { palette, unit })} {...rest} />;
}

export function LossTrendChart({
  trend,
  palette,
  ...rest
}: BaseChartProps & { trend: LossTrend }) {
  return <EChart option={buildLossTrendOption(trend, { palette })} {...rest} />;
}

export function ActualVsExpectedChart({
  points,
  palette,
  ...rest
}: BaseChartProps & { points: PeerComparisonPoint[] }) {
  return <EChart option={buildActualVsExpectedOption(points, { palette })} {...rest} />;
}

export function PeerComparisonChart({
  points,
  palette,
  ...rest
}: BaseChartProps & { points: PeerComparisonPoint[] }) {
  return <EChart option={buildPeerComparisonOption(points, { palette })} {...rest} />;
}

export function EnergyWaterfallChart({
  reconciliation,
  palette,
  ...rest
}: BaseChartProps & { reconciliation: Pick<TransformerReconciliation, "waterfall"> }) {
  return <EChart option={buildEnergyWaterfallOption(reconciliation, { palette })} {...rest} />;
}

export function RiskDistributionChart({
  breakdown,
  palette,
  ...rest
}: BaseChartProps & { breakdown: { tier: RiskTier; count: number }[] }) {
  return <EChart option={buildRiskDistributionOption(breakdown, { palette })} {...rest} />;
}

export function PrecisionRecallChart({
  points,
  palette,
  ...rest
}: BaseChartProps & { points: PrecisionRecallPoint[] }) {
  return <EChart option={buildPrecisionRecallOption(points, { palette })} {...rest} />;
}

export function CalibrationChart({
  points,
  palette,
  ...rest
}: BaseChartProps & { points: CalibrationPoint[] }) {
  return <EChart option={buildCalibrationOption(points, { palette })} {...rest} />;
}
