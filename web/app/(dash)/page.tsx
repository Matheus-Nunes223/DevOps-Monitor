import { OverviewLive } from "@/components/overview-live";
import { readOverviewSnapshot } from "@/lib/overview";
import { createClient } from "@/lib/supabase/server";

export default async function OverviewPage() {
  const supabase = await createClient();
  const initial = await readOverviewSnapshot(supabase);
  return <OverviewLive initial={initial} />;
}
