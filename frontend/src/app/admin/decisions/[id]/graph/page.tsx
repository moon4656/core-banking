import { DecisionGraphClient } from "./GraphClient";

export default async function DecisionGraphPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DecisionGraphClient requestId={decodeURIComponent(id)} />;
}
