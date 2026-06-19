import { MissionDetail } from "@/features/inspections/mission-detail";

export default async function MissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MissionDetail id={id} />;
}
