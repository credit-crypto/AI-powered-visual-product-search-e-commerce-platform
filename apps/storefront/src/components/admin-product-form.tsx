"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import {
  createAdminProduct,
  slugifyProductName,
  uploadAdminProductImage,
} from "@/lib/api";

export function AdminProductForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("19.99");
  const [sku, setSku] = useState("");
  const [stock, setStock] = useState("25");
  const [files, setFiles] = useState<FileList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function onNameChange(value: string) {
    setName(value);
    if (!slugTouched) setSlug(slugifyProductName(value));
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setProgress(null);

    const priceCents = Math.round(Number.parseFloat(price || "0") * 100);
    if (!name.trim() || !slug.trim()) {
      setError("Name and slug are required");
      return;
    }
    if (!Number.isFinite(priceCents) || priceCents < 0) {
      setError("Enter a valid price");
      return;
    }

    startTransition(() => {
      void (async () => {
        try {
          setProgress("Creating product…");
          const created = await createAdminProduct({
            name: name.trim(),
            slug: slug.trim(),
            description: description.trim() || undefined,
            price_cents: priceCents,
            currency: "USD",
            sku: sku.trim() || undefined,
            stock_qty: Number.parseInt(stock || "0", 10) || 0,
          });

          const list = files ? Array.from(files) : [];
          for (let i = 0; i < list.length; i += 1) {
            const file = list[i];
            setProgress(`Uploading image ${i + 1}/${list.length}…`);
            await uploadAdminProductImage(created.id, file, file.name);
          }

          setProgress("Done — opening product…");
          router.push(`/admin/products/${created.id}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Create failed");
          setProgress(null);
        }
      })();
    });
  }

  return (
    <form onSubmit={onSubmit} className="max-w-xl space-y-5">
      <p className="rounded-md border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-100/80">
        MVP admin — no authentication. Do not expose this surface publicly without auth.
      </p>

      <label className="block space-y-1 text-sm">
        <span className="text-ink-100/70">Name</span>
        <input
          required
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
        />
      </label>

      <label className="block space-y-1 text-sm">
        <span className="text-ink-100/70">Slug</span>
        <input
          required
          value={slug}
          onChange={(event) => {
            setSlugTouched(true);
            setSlug(slugifyProductName(event.target.value) || event.target.value);
          }}
          className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
        />
      </label>

      <label className="block space-y-1 text-sm">
        <span className="text-ink-100/70">Description</span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={4}
          className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
        />
      </label>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block space-y-1 text-sm">
          <span className="text-ink-100/70">Price (USD)</span>
          <input
            required
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(event) => setPrice(event.target.value)}
            className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-ink-100/70">SKU</span>
          <input
            value={sku}
            onChange={(event) => setSku(event.target.value)}
            placeholder="auto from slug"
            className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-ink-100/70">Stock</span>
          <input
            type="number"
            min="0"
            step="1"
            value={stock}
            onChange={(event) => setStock(event.target.value)}
            className="w-full rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-ink-50 outline-none"
          />
        </label>
      </div>

      <label className="block space-y-1 text-sm">
        <span className="text-ink-100/70">Images</span>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={(event) => setFiles(event.target.files)}
          className="block w-full text-sm text-ink-100/60 file:mr-3 file:rounded-md file:border-0 file:bg-leaf-500 file:px-3 file:py-1.5 file:text-ink-900"
        />
        <span className="text-xs text-ink-100/40">
          Upload starts embedding automatically after create.
        </span>
      </label>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {progress ? <p className="text-sm text-leaf-400">{progress}</p> : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-leaf-500 px-4 py-2 text-sm font-medium text-ink-900 transition hover:bg-leaf-400 disabled:opacity-50"
        >
          {isPending ? "Saving…" : "Create product"}
        </button>
        <Link href="/admin/products" className="px-4 py-2 text-sm text-ink-100/70 hover:text-leaf-400">
          Cancel
        </Link>
      </div>
    </form>
  );
}
