"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Lock, Search, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { StudyStatsSection, TAB_INFO } from "@/components/dashboard/study-stats";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ADMIN_SECTIONS, getAdminUsers, getAdminUserStats, type AdminUser } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type SortKey = "last_active_at" | "created_at" | "words_seen" | "reviews_7d" | "claude_tokens";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "last_active_at", label: "Dernière activité" },
  { key: "created_at", label: "Inscription" },
  { key: "words_seen", label: "Mots vus" },
  { key: "reviews_7d", label: "Révisions 7 j" },
  { key: "claude_tokens", label: "Tokens Claude" },
];

const nf = (n: number) => n.toLocaleString("fr-FR");
const dateFr = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });

/** "il y a 3 h", "hier", "il y a 12 j". */
export function ago(iso: string | null, now = Date.now()): string {
  if (!iso) return "jamais";
  const ms = now - new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  const min = Math.max(0, Math.round(ms / 60_000));
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `il y a ${h} h`;
  const d = Math.round(h / 24);
  if (d === 1) return "hier";
  if (d < 60) return `il y a ${d} j`;
  return `il y a ${Math.round(d / 30)} mois`;
}

const totalQuestions = (u: AdminUser) => ADMIN_SECTIONS.reduce((n, s) => n + u.questions[s], 0);

export function AdminPage() {
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("last_active_at");
  const query = useQuery({ queryKey: ["admin-users"], queryFn: getAdminUsers, retry: false });

  const users = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = (query.data?.users ?? []).filter((u) => !term || u.email.toLowerCase().includes(term));
    return [...list].sort((a, b) => {
      const va = a[sort] ?? "";
      const vb = b[sort] ?? "";
      return va < vb ? 1 : va > vb ? -1 : 0;
    });
  }, [query.data, search, sort]);

  if (query.isError) {
    const forbidden = query.error instanceof ApiError && query.error.status === 403;
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
          <Lock className="h-6 w-6" />
          {forbidden ? "Cette page est réservée à l'administrateur." : "Impossible de charger les comptes."}
        </CardContent>
      </Card>
    );
  }
  if (query.isLoading || !query.data) return <Skeleton className="h-96 w-full" />;
  if (selected) return <UserDetail user={selected} onBack={() => setSelected(null)} />;

  const { summary } = query.data;
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          <ShieldCheck className="h-7 w-7 text-primary" />
          Admin
        </h1>
        <p className="mt-1 text-muted-foreground">
          Les comptes inscrits et leur activité, en lecture seule : uniquement des compteurs et des dates (ni mot de passe, ni
          textes, ni dessins).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile value={summary.users} label="comptes inscrits" sub={`+${summary.signups_7d} en 7 j · +${summary.signups_30d} en 30 j`} />
        <Tile value={summary.active_today} label="actifs aujourd'hui" sub={`${summary.active_7d} en 7 j · ${summary.active_30d} en 30 j`} />
        <Tile value={summary.reviews_7d} label="cartes révisées en 7 j" />
        <Tile value={summary.claude_tokens} label="tokens Claude (total)" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Inscriptions par semaine</CardTitle>
          <CardDescription>Nouveaux comptes sur les 12 dernières semaines (semaines commençant le lundi).</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={query.data.signups_per_week} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barCategoryGap="20%">
                <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="week"
                  stroke="var(--color-muted-foreground)"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(w: string) => `${w.slice(8, 10)}/${w.slice(5, 7)}`}
                />
                <YAxis stroke="var(--color-muted-foreground)" fontSize={10} tickLine={false} axisLine={false} width={28} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "var(--color-popover-foreground)", fontWeight: 600 }}
                  itemStyle={{ color: "var(--color-popover-foreground)" }}
                  cursor={{ fill: "var(--color-muted)", opacity: 0.6 }}
                  labelFormatter={(w) => `Semaine du ${dateFr(String(w))}`}
                  formatter={(v) => [`${v} compte${Number(v) > 1 ? "s" : ""}`, "Inscriptions"]}
                />
                <Bar dataKey="count" fill="var(--viz-vocab)" radius={[3, 3, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>Comptes ({users.length})</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:w-56">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Chercher un e-mail" className="pl-9" />
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              Trier par
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="h-10 rounded-md border border-input bg-background px-2 text-sm text-foreground"
              >
                {SORTS.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[56rem] text-left text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 font-medium">Compte</th>
                  <th className="py-2 pr-3 font-medium">Dernière activité</th>
                  <th className="py-2 pr-3 text-right font-medium">Jours actifs (30 j)</th>
                  <th className="py-2 pr-3 text-right font-medium">Mots vus · maîtrisés</th>
                  <th className="py-2 pr-3 text-right font-medium">Révisions · 7 j</th>
                  <th className="py-2 pr-3 text-right font-medium">Questions d&apos;exercices</th>
                  <th className="py-2 pr-3 text-right font-medium">Textes · dessins</th>
                  <th className="py-2 text-right font-medium">Claude</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.id}
                    onClick={() => setSelected(u)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-accent/40"
                  >
                    <td className="py-2 pr-3">
                      <button type="button" className="text-left font-medium hover:underline" onClick={() => setSelected(u)}>
                        {u.email}
                      </button>
                      <span className="block text-xs text-muted-foreground">
                        inscrit le {dateFr(u.created_at)} · HSK {u.hsk_version}
                      </span>
                    </td>
                    <td className="whitespace-nowrap py-2 pr-3">
                      <span className={cn(u.active_today && "font-medium text-emerald-700 dark:text-emerald-300")}>{ago(u.last_active_at)}</span>
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{u.active_days_30}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {nf(u.words_seen)} · {nf(u.words_mastered)}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {nf(u.reviews)} · {nf(u.reviews_7d)}
                    </td>
                    <td
                      className="py-2 pr-3 text-right tabular-nums"
                      title={ADMIN_SECTIONS.map((s) => `${TAB_INFO[s].label} : ${u.questions[s]}`).join("\n")}
                    >
                      {nf(totalQuestions(u))}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {u.expressions} · {u.drawings}
                    </td>
                    <td className="whitespace-nowrap py-2 text-right tabular-nums">
                      {nf(u.claude_calls)} appels
                      <span className="block text-xs text-muted-foreground">{nf(u.claude_tokens)} tokens</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {users.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">Aucun compte ne correspond.</p>}
        </CardContent>
      </Card>
    </div>
  );
}

function Tile({ value, label, sub }: { value: number; label: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <p className="text-2xl font-semibold tabular-nums">{nf(value)}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

function UserDetail({ user, onBack }: { user: AdminUser; onBack: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Button variant="ghost" size="sm" onClick={onBack} className="self-start">
          <ArrowLeft className="h-4 w-4" />
          Tous les comptes
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight">{user.email}</h1>
        <p className="text-sm text-muted-foreground">
          Inscrit le {dateFr(user.created_at)} · HSK {user.hsk_version} · dernière activité {ago(user.last_active_at)}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile value={user.words_seen} label="mots vus" sub={`${nf(user.words_mastered)} maîtrisés`} />
        <Tile value={user.reviews} label="cartes révisées" sub={`${nf(user.reviews_7d)} ces 7 derniers jours`} />
        <Tile value={totalQuestions(user)} label="questions d'exercices" sub={ADMIN_SECTIONS.filter((s) => user.questions[s]).map((s) => `${TAB_INFO[s].label} ${user.questions[s]}`).join(" · ") || undefined} />
        <Tile value={user.claude_calls} label="appels à Claude" sub={`${nf(user.claude_tokens)} tokens`} />
      </div>
      <StudyStatsSection
        queryKey={["admin-user-stats", user.id]}
        load={async (days) => (await getAdminUserStats(user.id, days)).stats}
      />
    </div>
  );
}
