"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { SEARCH_RESULTS_KEY, searchByImage } from "@/lib/api";

async function blobFromCapacitorCamera(): Promise<{ blob: Blob; name: string } | null> {
  try {
    const { Camera, CameraResultType, CameraSource } = await import("@capacitor/camera");
    const photo = await Camera.getPhoto({
      quality: 85,
      resultType: CameraResultType.Uri,
      source: CameraSource.Prompt,
      width: 1280,
    });
    if (!photo.webPath) return null;
    const response = await fetch(photo.webPath);
    const blob = await response.blob();
    return { blob, name: `capture.${photo.format || "jpeg"}` };
  } catch {
    return null;
  }
}

type CatalogueSearchProps = {
  initialQuery?: string;
  /** When true, text search navigates to /products?q=… instead of staying on page */
  navigateOnTextSearch?: boolean;
  onTextSearch?: (q: string) => void;
  compact?: boolean;
};

export function CatalogueSearch({
  initialQuery = "",
  navigateOnTextSearch = true,
  onTextSearch,
  compact = false,
}: CatalogueSearchProps) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState(initialQuery);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function submitText(event?: React.FormEvent) {
    event?.preventDefault();
    const q = query.trim();
    setError(null);
    if (onTextSearch) {
      onTextSearch(q);
      return;
    }
    if (navigateOnTextSearch) {
      const href = q ? `/products?q=${encodeURIComponent(q)}` : "/products";
      startTransition(() => router.push(href));
    }
  }

  async function runImageSearch(file: Blob, name: string) {
    setError(null);
    try {
      const result = await searchByImage(file, name);
      sessionStorage.setItem(SEARCH_RESULTS_KEY, JSON.stringify(result));
      startTransition(() => router.push("/search/results"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image search failed");
    }
  }

  async function onImageClick() {
    setError(null);
    const captured = await blobFromCapacitorCamera();
    if (!captured) {
      fileRef.current?.click();
      return;
    }
    startTransition(() => {
      void runImageSearch(captured.blob, captured.name);
    });
  }

  return (
    <div className={compact ? "w-full max-w-xl" : "w-full"}>
      <form onSubmit={submitText} className="flex items-stretch gap-0 overflow-hidden rounded-md border border-white/15 bg-ink-900/80">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search products…"
          className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-ink-50 outline-none placeholder:text-ink-100/40"
          aria-label="Search products"
        />
        <button
          type="submit"
          disabled={isPending}
          className="border-l border-white/10 px-3 text-sm text-ink-100/80 transition hover:text-leaf-400 disabled:opacity-50"
        >
          Search
        </button>
        <button
          type="button"
          onClick={() => void onImageClick()}
          disabled={isPending}
          title="Search by photo"
          aria-label="Search by photo"
          className="inline-flex items-center border-l border-white/10 px-3 text-leaf-400 transition hover:bg-leaf-500/10 disabled:opacity-50"
        >
          {isPending ? (
            "…"
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M4 8h3l1.5-2h7L17 8h3a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2Z"
                stroke="currentColor"
                strokeWidth="1.6"
              />
              <circle cx="12" cy="13" r="3.2" stroke="currentColor" strokeWidth="1.6" />
            </svg>
          )}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            startTransition(() => {
              void runImageSearch(file, file.name);
            });
            event.target.value = "";
          }}
        />
      </form>
      {error ? <p className="mt-1 text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
