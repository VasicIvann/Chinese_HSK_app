"use client";

import { motion } from "framer-motion";
import { ArrowRight, BrainCircuit, PencilLine, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { TopNav } from "@/components/top-nav";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";

const FEATURES = [
  {
    icon: BrainCircuit,
    title: "Révisions SRS (FSRS)",
    description:
      "Algorithme moderne qui te montre chaque mot juste avant que tu l'oublies. Optimal pour ta préparation.",
  },
  {
    icon: PencilLine,
    title: "Expression écrite corrigée",
    description:
      "Rédige en chinois, Claude analyse, identifie tes erreurs et te renvoie une version corrigée commentée.",
  },
  {
    icon: Sparkles,
    title: "Sujets adaptés à ton niveau",
    description:
      "Pool de sujets curatés + génération à la demande, calés sur le vocabulaire HSK que tu maîtrises.",
  },
];

export default function LandingPage() {
  const router = useRouter();
  const { isAuthenticated, isHydrating } = useAuth();

  useEffect(() => {
    if (!isHydrating && isAuthenticated) {
      router.replace("/comprehension");
    }
  }, [isAuthenticated, isHydrating, router]);

  return (
    <div className="flex min-h-full flex-col">
      <TopNav />
      <main className="flex-1">
        <section className="mx-auto max-w-5xl px-4 pb-12 pt-16 sm:px-6 lg:pt-24">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mx-auto max-w-2xl text-center"
          >
            <p className="hanzi text-5xl text-primary">学习 中文</p>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight sm:text-5xl">
              Progresse en chinois, sans flashcards stériles
            </h1>
            <p className="mt-5 text-lg text-muted-foreground">
              HSK Trainer combine un planificateur de révisions FSRS et une
              correction d'expression écrite par IA pour transformer ta
              préparation à l'examen.
            </p>
            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Button asChild size="lg">
                <Link href="/signup">
                  Créer un compte gratuit
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/signin">J'ai déjà un compte</Link>
              </Button>
            </div>
          </motion.div>
        </section>

        <section className="mx-auto max-w-5xl px-4 pb-24 sm:px-6">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature, idx) => (
              <motion.article
                key={feature.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 * idx, ease: "easeOut" }}
                className="rounded-xl border border-border bg-card p-6 shadow-sm"
              >
                <feature.icon className="h-8 w-8 text-primary" />
                <h3 className="mt-4 text-lg font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </motion.article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
