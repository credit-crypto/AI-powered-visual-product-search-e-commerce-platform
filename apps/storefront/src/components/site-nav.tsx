"use client";

import Link from "next/link";

import { CatalogueSearch } from "@/components/catalogue-search";

const links = [
  { href: "/products", label: "Products" },
  { href: "/cart", label: "Cart" },
  { href: "/checkout", label: "Checkout" },
  { href: "/account/orders", label: "Orders" },
  { href: "/admin", label: "Admin" },
];

export function SiteNav() {
  return (
    <header className="border-b border-white/10 bg-ink-900/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Link href="/" className="font-display text-xl tracking-tight text-leaf-400">
            Visual Shop
          </Link>
          <nav className="flex flex-wrap gap-3 text-sm text-ink-100/80">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="transition hover:text-leaf-400"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <CatalogueSearch compact />
      </div>
    </header>
  );
}
