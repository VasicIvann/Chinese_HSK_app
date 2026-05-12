"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/comprehension", label: "Compréhension" },
  { href: "/expression", label: "Expression" },
  { href: "/account", label: "Compte" },
];

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSignOut = () => {
    signOut();
    setMobileOpen(false);
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link
          href={isAuthenticated ? "/comprehension" : "/"}
          className="flex items-center gap-2 font-semibold tracking-tight"
        >
          <span className="hanzi text-2xl text-primary">学</span>
          <span>HSK Trainer</span>
        </Link>

        {isAuthenticated && (
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        )}

        <div className="flex items-center gap-1">
          <ThemeToggle />
          {isAuthenticated ? (
            <>
              <span className="hidden text-sm text-muted-foreground md:inline">
                {user?.email}
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Se déconnecter"
                onClick={handleSignOut}
                className="hidden md:inline-flex"
              >
                <LogOut className="h-5 w-5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Menu"
                onClick={() => setMobileOpen((v) => !v)}
                className="md:hidden"
              >
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Button asChild variant="ghost" size="sm">
                <Link href="/signin">Se connecter</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/signup">Créer un compte</Link>
              </Button>
            </div>
          )}
        </div>
      </div>

      {isAuthenticated && mobileOpen && (
        <nav className="border-t border-border bg-background md:hidden">
          <ul className="flex flex-col p-2">
            {NAV_LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "block rounded-md px-4 py-3 text-base font-medium",
                      active
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                    )}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
            <li>
              <button
                onClick={handleSignOut}
                className="flex w-full items-center gap-2 rounded-md px-4 py-3 text-left text-base font-medium text-destructive hover:bg-destructive/10"
              >
                <LogOut className="h-5 w-5" />
                Se déconnecter
              </button>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
