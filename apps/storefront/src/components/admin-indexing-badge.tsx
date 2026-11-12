import { indexingStatusLabel } from "@/lib/api";

const STYLES: Record<string, string> = {
  ready: "text-leaf-400 border-leaf-400/40 bg-leaf-500/10",
  pending: "text-amber-200 border-amber-400/30 bg-amber-400/10",
  indexing: "text-sky-200 border-sky-400/30 bg-sky-400/10",
  failed: "text-red-300 border-red-400/40 bg-red-500/10",
  partial_failed: "text-orange-200 border-orange-400/30 bg-orange-400/10",
  no_images: "text-ink-100/60 border-white/15 bg-white/5",
};

export function AdminIndexingBadge({ status }: { status: string }) {
  const style = STYLES[status] || STYLES.no_images;
  return (
    <span className={`inline-flex rounded border px-2 py-0.5 text-xs ${style}`}>
      {indexingStatusLabel(status)}
    </span>
  );
}
