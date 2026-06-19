import { TransformerTwin } from "@/features/assets/transformer-twin";

export default async function TransformerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <TransformerTwin id={id} />;
}
