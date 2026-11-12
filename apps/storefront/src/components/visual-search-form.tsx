"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, useTransition } from "react";

import {
  SEARCH_RESULTS_KEY,
  searchByImage,
  type VisualSearchResponse,
} from "@/lib/api";

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
    // Not running inside Capacitor or plugin unavailable — fall back to file input.
    return null;
  }
}

export function VisualSearchForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [lastMeta, setLastMeta] = useState<Pick<VisualSearchResponse, "query_ms" | "model_name"> | null>(
    null,
  );

  function rememberAndGo(payload: VisualSearchResponse) {
    sessionStorage.setItem(SEARCH_RESULTS_KEY, JSON.stringify(payload));
    setLastMeta({ query_ms: payload.query_ms, model_name: payload.model_name });
    startTransition(() => {
      router.push("/search/results");
    });
  }

  async function runSearch(file: Blob, name: string) {
    setError(null);
    try {
      const result = await searchByImage(file, name);
      rememberAndGo(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPreviewUrl(URL.createObjectURL(file));
    startTransition(() => {
      void runSearch(file, file.name);
    });
  }

  async function onCameraClick() {
    setError(null);
    const captured = await blobFromCapacitorCamera();
    if (!captured) {
      inputRef.current?.click();
      return;
    }
    setPreviewUrl(URL.createObjectURL(captured.blob));
    startTransition(() => {
      void runSearch(captured.blob, captured.name);
    });
  }

  return (
    <div className="space-y-4">
      <div className="space-y-4 border border-dashed border-white/20 p-6">
        <label className="block space-y-2 text-sm">
          <span className="text-ink-100/80">Product photo</span>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={onFileChange}
            disabled={isPending}
            className="block w-full text-sm text-ink-100/60 file:mr-4 file:rounded-md file:border-0 file:bg-leaf-500 file:px-3 file:py-1.5 file:text-ink-900"
          />
        </label>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void onCameraClick()}
            disabled={isPending}
            className="rounded-md bg-leaf-500 px-4 py-2 text-sm font-medium text-ink-900 transition hover:bg-leaf-400 disabled:opacity-50"
          >
            {isPending ? "Searching…" : "Camera / upload"}
          </button>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={isPending}
            className="rounded-md border border-white/15 px-4 py-2 text-sm text-ink-100 transition hover:border-leaf-400/50 disabled:opacity-50"
          >
            Choose file
          </button>
        </div>

        <p className="text-xs text-ink-100/50">
          Posts to <code className="text-leaf-400">POST /api/v1/search/image</code>. On device,
          Capacitor Camera is used when available; otherwise the file picker (with{" "}
          <code>capture</code>) opens.
        </p>
      </div>

      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt="Query preview"
          className="max-h-56 rounded-md border border-white/10 object-contain"
        />
      ) : null}

      {lastMeta?.model_name ? (
        <p className="text-xs text-ink-100/50">
          Last model: {lastMeta.model_name}
          {lastMeta.query_ms != null ? ` · ${lastMeta.query_ms} ms` : null}
        </p>
      ) : null}

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
