import { SearchResultsView } from "@/components/search-results-view";

export default function SearchResultsPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Search results</h1>
      <p className="text-ink-100/70">Top visually similar products from your last query.</p>
      <SearchResultsView />
    </section>
  );
}
