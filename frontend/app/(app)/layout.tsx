"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { TopNav } from "@/components/top-nav";
import { useAuth } from "@/lib/auth/auth-context";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, isHydrating } = useAuth();

  useEffect(() => {
    if (!isHydrating && !isAuthenticated) {
      router.replace("/signin");
    }
  }, [isAuthenticated, isHydrating, router]);

  if (isHydrating || !isAuthenticated) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Chargement…
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-col">
      <TopNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 lg:py-10">
        {children}
      </main>
    </div>
  );
}
