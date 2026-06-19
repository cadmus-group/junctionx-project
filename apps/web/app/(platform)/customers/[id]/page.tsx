import { CustomerInvestigation } from "@/features/customers/customer-investigation";

export default async function CustomerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CustomerInvestigation id={id} />;
}
