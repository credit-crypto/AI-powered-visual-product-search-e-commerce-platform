export default function VisualSearchPage() {
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl text-ink-50">Visual search</h1>
        <p className="text-ink-100/70">
          Upload an image to find similar products. Camera capture via Capacitor will land here
          for mobile.
        </p>
      </div>
      <form className="space-y-4 border border-dashed border-white/20 p-6">
        <label className="block space-y-2 text-sm">
          <span className="text-ink-100/80">Product photo</span>
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="block w-full text-sm text-ink-100/60 file:mr-4 file:rounded-md file:border-0 file:bg-leaf-500 file:px-3 file:py-1.5 file:text-ink-900"
            disabled
          />
        </label>
        <p className="text-xs text-ink-100/50">
          Stub UI — posts to <code className="text-leaf-400">POST /api/v1/search/image</code> once
          the encoder is live.
        </p>
        <button
          type="button"
          disabled
          className="rounded-md bg-leaf-500/40 px-4 py-2 text-sm text-ink-900/70"
        >
          Search (coming soon)
        </button>
      </form>
    </section>
  );
}
