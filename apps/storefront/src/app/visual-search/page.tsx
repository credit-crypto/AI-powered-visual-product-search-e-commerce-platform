import { VisualSearchForm } from "@/components/visual-search-form";

export default function VisualSearchPage() {
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl text-ink-50">Visual search</h1>
        <p className="text-ink-100/70">
          Upload a photo or use the camera to find visually similar products in the catalogue.
        </p>
      </div>
      <VisualSearchForm />
    </section>
  );
}
