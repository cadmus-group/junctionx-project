export { EChart, type EChartProps } from "./components/echart";
export {
  TimeSeriesChart,
  LossTrendChart,
  ActualVsExpectedChart,
  PeerComparisonChart,
  EnergyWaterfallChart,
  RiskDistributionChart,
  PrecisionRecallChart,
  CalibrationChart,
  type BaseChartProps,
} from "./components/charts";

export {
  buildLossTrendOption,
  buildTimeSeriesOption,
  buildActualVsExpectedOption,
  buildPeerComparisonOption,
  buildEnergyWaterfallOption,
  buildRiskDistributionOption,
  buildPrecisionRecallOption,
  buildCalibrationOption,
  precisionRecallFromModel,
  DEFAULT_PALETTE,
  RISK_TIER_SEQUENCE,
  riskTierColor,
  type ChartPalette,
  type OptionArgs,
  type TimeSeriesSeries,
  type PrecisionRecallPoint,
  type CalibrationPoint,
} from "./options";
