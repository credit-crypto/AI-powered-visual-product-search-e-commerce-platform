import Link from "next/link";

export default function HomePage() {
  return (
    <section className="space-y-8">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-[0.2em] text-leaf-400/80">Visual Shop</p>
        <h1 className="font-display text-4xl leading-tight text-ink-50 sm:text-5xl">
          Find products by what they look like.
        </h1>
        <p className="max-w-xl text-lg text-ink-100/70">
          Upload a photo or snap one on your phone — we match it against the catalogue with
          AI visual search.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/visual-search"
          className="rounded-md bg-leaf-500 px-5 py-2.5 text-sm font-medium text-ink-900 transition hover:bg-leaf-400"
        >
          Try visual search
        </Link>
        <Link
          href="/products"
          className="rounded-md border border-white/15 px-5 py-2.5 text-sm text-ink-100 transition hover:border-leaf-400/50"
        >
          Browse products
        </Link>
      </div>
    </section>
  );
}
