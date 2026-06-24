import { DecisionTraceClient } from "./TraceClient";

export default async function DecisionTracePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DecisionTraceClient requestId={decodeURIComponent(id)} />;
}
