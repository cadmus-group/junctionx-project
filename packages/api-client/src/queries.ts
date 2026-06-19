import { queryOptions } from "@tanstack/react-query";
import type {
  AssetCustomerSummary,
  CustomerReadings,
  CustomerRiskProfile,
  DashboardSummary,
  FeatureCollection,
  GridAsset,
  HealthResponse,
  InspectionMission,
  InspectionQueueItem,
  LossTrend,
  ModelRegistryEntry,
  Page,
  TransformerReconciliation,
  Customer,
} from "@gridtrace/contracts";
import type { GridTraceClient } from "./client";
import { queryKeys } from "./query-keys";

const V1 = "api/v1";

export function dashboardQueries(client: GridTraceClient) {
  return {
    summary: (params?: { from?: string; to?: string; regionId?: string }) =>
      queryOptions({
        queryKey: queryKeys.dashboard.summary(params),
        queryFn: ({ signal }) =>
          client.request<DashboardSummary>(`${V1}/dashboard/summary`, { query: params, signal }),
      }),
    lossTrend: (params?: { from?: string; to?: string; regionId?: string }) =>
      queryOptions({
        queryKey: queryKeys.dashboard.lossTrend(params),
        queryFn: ({ signal }) =>
          client.request<LossTrend>(`${V1}/dashboard/loss-trend`, { query: params, signal }),
      }),
  };
}

export function gisQueries(client: GridTraceClient) {
  return {
    anomalies: (params?: {
      min_lon?: number;
      min_lat?: number;
      max_lon?: number;
      max_lat?: number;
      min_risk?: number;
    }) =>
      queryOptions({
        queryKey: queryKeys.gis.anomalies(params),
        queryFn: ({ signal }) =>
          client.request<FeatureCollection>(`${V1}/gis/anomalies/geojson`, {
            query: params,
            signal,
          }),
      }),
    hotspots: (params?: { resolution?: number; min_risk?: number }) =>
      queryOptions({
        queryKey: queryKeys.gis.hotspots(params),
        queryFn: ({ signal }) =>
          client.request<FeatureCollection>(`${V1}/gis/hotspots`, { query: params, signal }),
      }),
  };
}

export function assetQueries(client: GridTraceClient) {
  return {
    list: (params?: { page?: number; page_size?: number; asset_type?: string; q?: string }) =>
      queryOptions({
        queryKey: queryKeys.assets.list(params),
        queryFn: ({ signal }) =>
          client.request<Page<GridAsset>>(`${V1}/assets`, { query: params, signal }),
      }),
    detail: (id: string) =>
      queryOptions({
        queryKey: queryKeys.assets.detail(id),
        queryFn: ({ signal }) => client.request<GridAsset>(`${V1}/assets/${id}`, { signal }),
      }),
    reconciliation: (id: string) =>
      queryOptions({
        queryKey: queryKeys.assets.reconciliation(id),
        queryFn: ({ signal }) =>
          client.request<TransformerReconciliation>(
            `${V1}/assets/transformers/${id}/reconciliation`,
            { signal }
          ),
      }),
    customers: (id: string, params?: { page?: number; page_size?: number }) =>
      queryOptions({
        queryKey: queryKeys.assets.customers(id, params),
        queryFn: ({ signal }) =>
          client.request<Page<AssetCustomerSummary>>(`${V1}/assets/${id}/customers`, {
            query: params,
            signal,
          }),
      }),
  };
}

export function customerQueries(client: GridTraceClient) {
  return {
    list: (params?: {
      page?: number;
      page_size?: number;
      min_risk?: number;
      tier?: string;
      q?: string;
    }) =>
      queryOptions({
        queryKey: queryKeys.customers.list(params),
        queryFn: ({ signal }) =>
          client.request<Page<Customer>>(`${V1}/customers`, { query: params, signal }),
      }),
    detail: (id: string) =>
      queryOptions({
        queryKey: queryKeys.customers.detail(id),
        queryFn: ({ signal }) => client.request<Customer>(`${V1}/customers/${id}`, { signal }),
      }),
    readings: (id: string, params?: { from?: string; to?: string }) =>
      queryOptions({
        queryKey: queryKeys.customers.readings(id, params),
        queryFn: ({ signal }) =>
          client.request<CustomerReadings>(`${V1}/customers/${id}/readings`, {
            query: params,
            signal,
          }),
      }),
    riskProfile: (id: string) =>
      queryOptions({
        queryKey: queryKeys.customers.riskProfile(id),
        queryFn: ({ signal }) =>
          client.request<CustomerRiskProfile>(`${V1}/customers/${id}/risk-profile`, { signal }),
      }),
  };
}

export function riskQueries(client: GridTraceClient) {
  // Risk data is surfaced via customer/asset/gis endpoints; grouped here for discoverability.
  return {
    ...customerQueries(client),
    ...gisQueries(client),
  };
}

export function inspectionQueries(client: GridTraceClient) {
  return {
    queue: (params?: { page?: number; page_size?: number; region_id?: string }) =>
      queryOptions({
        queryKey: queryKeys.inspections.queue(params),
        queryFn: ({ signal }) =>
          client.request<Page<InspectionQueueItem>>(`${V1}/inspections/queue`, {
            query: params,
            signal,
          }),
      }),
    missions: () =>
      queryOptions({
        queryKey: queryKeys.inspections.missions(),
        queryFn: ({ signal }) =>
          client.request<Page<InspectionMission>>(`${V1}/inspections/missions`, { signal }),
      }),
  };
}

export function modelQueries(client: GridTraceClient) {
  return {
    list: () =>
      queryOptions({
        queryKey: queryKeys.models.list(),
        queryFn: ({ signal }) =>
          client.request<ModelRegistryEntry[]>(`${V1}/models`, { signal }),
      }),
  };
}

export function healthQuery(client: GridTraceClient) {
  return queryOptions({
    queryKey: queryKeys.health(),
    queryFn: ({ signal }) => client.request<HealthResponse>(`${V1}/health`, { signal }),
  });
}
