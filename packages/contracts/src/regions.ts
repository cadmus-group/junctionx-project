export interface Region {
  id: string;
  code: string;
  name: string;
  region_type: string;
  parent_region_id: string | null;
}
