/** RFC 7807 problem details. */
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  [key: string]: unknown;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export type EntityType = "customer" | "transformer" | "feeder" | "region";

export type AssetType =
  | "substation"
  | "feeder"
  | "transformer"
  | "distribution_line"
  | "meter";

export interface AuthLoginRequest {
  email: string;
  password: string;
}

export interface AuthLoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: { id: string; email: string; name: string; role: string };
}

export interface Quantity {
  value: number;
  unit: string;
}
