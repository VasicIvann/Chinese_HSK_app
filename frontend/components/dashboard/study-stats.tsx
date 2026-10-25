"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, BookOpenText, Clock } from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getStudyStats, STAT_PERIODS, TABS, type StatPeriod, type StatTab, type StudyStats } from "@/lib/api/stats";
import { useHskVersion } from "@/lib/hsk-version";
import { cn } from "@/lib/utils";

/** Name of each tab and the unit of its daily count (kept separate: one small chart per tab). */
export const TAB_INFO: Record<StatTab, { label: string; unit: string; one: string }> = {
  vocab: { label: "Vocabulaire", unit: "cartes", one: "carte" },
  listening: { label: "Écoute", unit: "questions", one: "question" },
  writing: { label: "Écriture HSK", unit: "questions", one: "question" },
  grammar: { label: "Grammaire", unit: "questions", one: "question" },
  classifiers: { label: "Classificateurs", unit: "questions", one: "question" },
  tones: { label: "Tons", unit: "mots", one: "mot" },
  expression: { label: "Expression", unit: "textes", one: "texte" },
  drawings: { label: "Dessins", unit: "dessins", one: "dessin" },
};

const WEEKDAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const WEEKDAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];
const AXIS = { stroke: "var(--color-muted-foreground)", fontSize: 10, tickLine: false, axisLine: false } as const;
const TOOLTIP = {
  contentStyle: {
    background: "var(--color-popover)",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    fontSize: 12,
  },
  labelStyle: { color: "var(--color-popover-foreground)", fontWeight: 600 },
  itemStyle: { color: "var(--color-popover-foreground)" },
  cursor: { fill: "var(--color-muted)", opacity: 0.6 },
} as const;

const day = (iso: string) => new Date(`${iso}T12:00:00`);
const shortDate = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const longDate = (iso: unknown) =>
  typeof iso === "string" ? day(iso).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" }) : "";
const plural = (n: number, one: string, many: string) => `${n.toLocaleString("fr-FR")} ${n > 1 ? many : one}`;
const minutesText = (m: number) => (m < 60 ? `${Math.round(m)} min` : `${Math.floor(m / 60)} h ${String(Math.round(m % 60)).padStart(2, "0")}`);

export function StudyStatsSection() {
  const { version } = useHskVersion();
  const [days, setDays] = useState<StatPeriod>(30);
  const query = useQuery({ queryKey: ["study-stats", days, version], queryFn: () => getStudyStats(days, version) });
  const stats = query.data;

  return (
    <section className="flex flex-col gap-4" aria-labelledby="study-stats-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="study-stats-title" className="text-xl font-semibold tracking-tight">
            Statistiques d&apos;étude
          </h2>
          <p className="text-sm text-muted-foreground">
            {stats
              ? `${plural(stats.active_days, "jour actif", "jours actifs")} sur ${stats.days} · du ${longDate(stats.from_date)} au ${longDate(stats.to_date)}`
              : "Ton activité jour par jour, sur chaque onglet du site."}
          </p>
        </div>
        <div role="radiogroup" aria-label="Période" className="flex gap-1 rounded-lg bg-muted p-1">
          {STAT_PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              role="radio"
              aria-checked={days === p}
              onClick={() => setDays(p)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                days === p ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {p} jours
            </button>
          ))}
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : !stats ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">Impossible de charger les statistiques.</CardContent>
        </Card>
      ) : (
        <>
          <TabActivity stats={stats} />
          <WordsGrowth stats={stats} />
          <TimeAndHabits stats={stats} />
        </>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------- activity per tab

function TabActivity({ stats }: { stats: StudyStats }) {
  const active = TABS.filter((t) => stats.totals[t] > 0);
  const idle = TABS.filter((t) => stats.totals[t] === 0);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Activité par onglet
        </CardTitle>
        <CardDescription>Ce que tu as fait chaque jour sur chaque onglet. Chaque graphique a sa propre échelle.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {active.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Aucune activité sur cette période.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {active.map((tab) => (
              <TabChart key={tab} tab={tab} stats={stats} />
            ))}
          </div>
        )}
        {idle.length > 0 && active.length > 0 && (
          <p className="text-xs text-muted-foreground">Rien sur la période : {idle.map((t) => TAB_INFO[t].label).join(", ")}.</p>
        )}
        {active.length > 0 && <ActivityTable stats={stats} tabs={active} />}
      </CardContent>
    </Card>
  );
}

function TabChart({ tab, stats }: { tab: StatTab; stats: StudyStats }) {
  const info = TAB_INFO[tab];
  const total = stats.totals[tab];
  const activeDays = stats.activity.filter((d) => d[tab] > 0).length;
  return (
    <figure className="flex flex-col gap-2 rounded-lg border border-border p-3" aria-label={`${info.label} par jour`}>
      <figcaption className="flex items-baseline justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: `var(--viz-${tab})` }} />
          {info.label}
        </span>
        <span className="text-sm">
          <span className="font-semibold">{total.toLocaleString("fr-FR")}</span>{" "}
          <span className="text-muted-foreground">{total > 1 ? info.unit : info.one}</span>
        </span>
      </figcaption>
      <div className="h-24 sm:h-28">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={stats.activity} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barCategoryGap="15%">
            <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
            <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} interval="preserveStartEnd" minTickGap={24} />
            <YAxis {...AXIS} width={28} allowDecimals={false} tickCount={3} />
            <Tooltip
              {...TOOLTIP}
              labelFormatter={longDate}
              formatter={(value) => [plural(Number(value), info.one, info.unit), info.label]}
            />
            <Bar dataKey={tab} fill={`var(--viz-${tab})`} radius={[3, 3, 0, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted-foreground">
        {plural(activeDays, "jour", "jours")} · {plural(Math.round(total / Math.max(1, activeDays)), info.one, info.unit)} par jour actif
      </p>
    </figure>
  );
}

function ActivityTable({ stats, tabs }: { stats: StudyStats; tabs: StatTab[] }) {
  const rows = stats.activity.filter((d) => tabs.some((t) => d[t] > 0)).reverse();
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Voir les données en tableau</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[28rem] text-left">
          <thead className="text-xs text-muted-foreground">
            <tr>
              <th className="py-1 pr-3 font-medium">Jour</th>
              {tabs.map((t) => (
                <th key={t} className="py-1 pr-3 text-right font-medium">
                  {TAB_INFO[t].label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.date} className="border-t border-border">
                <td className="py-1 pr-3">{longDate(d.date)}</td>
                {tabs.map((t) => (
                  <td key={t} className="py-1 pr-3 text-right tabular-nums">
                    {d[t] || "·"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

// --------------------------------------------------------------------------- vocabulary growth

function WordsGrowth({ stats }: { stats: StudyStats }) {
  const { words } = stats;
  const levels = words.level_totals;
  // The axis goes up to the next level to reach (or the whole list once everything is seen).
  const next = levels.find((l) => l.total > words.seen_total) ?? levels[levels.length - 1];
  const top = Math.max(next?.total ?? 0, words.seen_total, 1);
  const shown = levels.filter((l) => l.total <= top);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpenText className="h-5 w-5 text-primary" />
          Évolution du vocabulaire
        </CardTitle>
        <CardDescription>Mots de la liste {stats.version === "2.0" ? "HSK 2.0" : "HSK 3.0"} déjà vus au moins une fois en quiz.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-3">
          <Figure value={words.seen_total} label="mots vus au total" />
          <Figure value={words.new_in_period} label={`nouveaux en ${stats.days} jours`} signed />
          <Figure value={words.reviewed_in_period} label="mots différents révisés" />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <figure className="flex flex-col gap-1" aria-label="Mots vus, cumulé">
            <figcaption className="text-sm font-medium">Mots vus (cumulé)</figcaption>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={words.per_day} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} interval="preserveStartEnd" minTickGap={28} />
                  <YAxis {...AXIS} width={36} domain={[0, top]} allowDecimals={false} />
                  {shown.map((l) => (
                    <ReferenceLine
                      key={l.level}
                      y={l.total}
                      stroke="var(--color-muted-foreground)"
                      strokeDasharray="4 4"
                      strokeOpacity={0.6}
                      label={{
                        value: `HSK 1${l.level > 1 ? `–${l.level}` : ""} · ${l.total}`,
                        position: "insideTopLeft",
                        fontSize: 10,
                        fill: "var(--color-muted-foreground)",
                      }}
                    />
                  ))}
                  <Tooltip
                    {...TOOLTIP}
                    cursor={{ stroke: "var(--color-muted-foreground)", strokeDasharray: "3 3" }}
                    labelFormatter={longDate}
                    formatter={(value) => [plural(Number(value), "mot vu", "mots vus"), "Total"]}
                  />
                  <Line
                    type="monotone"
                    dataKey="seen"
                    stroke="var(--viz-vocab)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                    activeDot={{ r: 4, stroke: "var(--color-card)", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <figure className="flex flex-col gap-1" aria-label="Nouveaux mots par jour">
            <figcaption className="text-sm font-medium">Nouveaux mots par jour</figcaption>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={words.per_day} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="15%">
                  <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} interval="preserveStartEnd" minTickGap={28} />
                  <YAxis {...AXIS} width={36} allowDecimals={false} />
                  <Tooltip
                    {...TOOLTIP}
                    labelFormatter={longDate}
                    formatter={(value) => [plural(Number(value), "nouveau mot", "nouveaux mots"), "Ce jour-là"]}
                  />
                  <Bar dataKey="new" fill="var(--viz-vocab)" radius={[3, 3, 0, 0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </figure>
        </div>
      </CardContent>
    </Card>
  );
}

function Figure({ value, label, signed }: { value: number; label: string; signed?: boolean }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xl font-semibold tabular-nums sm:text-2xl">
        {signed && value > 0 ? "+" : ""}
        {value.toLocaleString("fr-FR")}
      </p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

// --------------------------------------------------------------------------- time and habits

function TimeAndHabits({ stats }: { stats: StudyStats }) {
  const { time } = stats;
  const studied = time.per_day.filter((d) => d.minutes > 0);
  const avg = studied.length ? time.total_minutes / studied.length : 0;
  const totalActions = time.by_hour.reduce((n, h) => n + h.count, 0);
  const peak = time.by_hour.reduce((best, h) => (h.count > best.count ? h : best), time.by_hour[0]);
  const bestDay = time.by_weekday.reduce((best, w) => (w.count > best.count ? w : best), time.by_weekday[0]);
  const hours = time.by_hour.map((h) => ({ ...h, label: `${h.hour} h` }));
  const weekdays = time.by_weekday.map((w) => ({ ...w, label: WEEKDAYS[w.weekday] }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          Temps et habitudes
        </CardTitle>
        <CardDescription>
          Temps passé sur les cartes de vocabulaire (une carte laissée ouverte compte 2 min au plus), et quand tu étudies.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xl font-semibold tabular-nums sm:text-2xl">{minutesText(time.total_minutes)}</p>
            <p className="text-xs text-muted-foreground">sur les cartes en {stats.days} jours</p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xl font-semibold tabular-nums sm:text-2xl">{minutesText(avg)}</p>
            <p className="text-xs text-muted-foreground">par jour de quiz</p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xl font-semibold tabular-nums sm:text-2xl">{totalActions ? `${peak.hour} h` : "—"}</p>
            <p className="text-xs text-muted-foreground">
              heure la plus active{totalActions ? `, surtout le ${WEEKDAY_NAMES[bestDay.weekday]}` : ""}
            </p>
          </div>
        </div>

        <figure className="flex flex-col gap-1" aria-label="Minutes sur les cartes par jour">
          <figcaption className="text-sm font-medium">Minutes par jour (vocabulaire)</figcaption>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={time.per_day} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="15%">
                <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} interval="preserveStartEnd" minTickGap={28} />
                <YAxis {...AXIS} width={36} allowDecimals={false} />
                <Tooltip
                  {...TOOLTIP}
                  labelFormatter={longDate}
                  formatter={(value, _name, item) => [
                    `${minutesText(Number(value))} · ${plural(item.payload.cards, "carte", "cartes")}`,
                    "Temps",
                  ]}
                />
                <Bar dataKey="minutes" fill="var(--viz-vocab)" radius={[3, 3, 0, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </figure>

        <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <figure className="flex flex-col gap-1" aria-label="Activité selon l'heure">
            <figcaption className="text-sm font-medium">Selon l&apos;heure</figcaption>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={hours} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="12%">
                  <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="label" {...AXIS} interval={2} />
                  <YAxis {...AXIS} width={36} allowDecimals={false} />
                  <Tooltip
                    {...TOOLTIP}
                    labelFormatter={(l) => `De ${String(l).replace(" h", "")} h à ${Number(String(l).replace(" h", "")) + 1} h`}
                    formatter={(value) => [plural(Number(value), "action", "actions"), "Activité"]}
                  />
                  <Bar dataKey="count" fill="var(--viz-drawings)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <figure className="flex flex-col gap-1" aria-label="Activité selon le jour de la semaine">
            <figcaption className="text-sm font-medium">Selon le jour</figcaption>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weekdays} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="15%">
                  <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="label" {...AXIS} interval={0} />
                  <YAxis {...AXIS} width={36} allowDecimals={false} />
                  <Tooltip {...TOOLTIP} formatter={(value) => [plural(Number(value), "action", "actions"), "Activité"]} />
                  <Bar dataKey="count" fill="var(--viz-drawings)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </figure>
        </div>
        <p className="text-xs text-muted-foreground">Une action = une carte, une question d&apos;exercice, un texte ou un dessin.</p>
      </CardContent>
    </Card>
  );
}
