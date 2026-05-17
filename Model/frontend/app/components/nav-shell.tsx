"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, House, Sparkles } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: House },
  { href: "/recommend", label: "Recommend", icon: Sparkles },
  { href: "/offers", label: "Browse Offers", icon: Compass },
];

export default function NavShell() {
  const pathname = usePathname();

  return (
    <header className="nav-shell">
      <Link href="/" className="brand-mark" aria-label="Go to home">
        <span className="brand-orbit" aria-hidden="true" />
        <span className="brand-copy">
          <strong>Job Intelligent</strong>
          <em>Data Career Radar</em>
        </span>
      </Link>

      <nav className="nav-links" aria-label="Primary navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`nav-link ${active ? "is-active" : ""}`.trim()}
            >
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
