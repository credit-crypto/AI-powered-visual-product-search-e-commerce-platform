import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/products", label: "Products" },
  { href: "/visual-search", label: "Visual Search" },
  { href: "/search/results", label: "Results" },
  { href: "/cart", label: "Cart" },
  { href: "/admin", label: "Admin" },
];

export function SiteNav() {
  return (
    <header className="border-b border-white/10 bg-ink-900/70 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
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
    </header>
  );
}
