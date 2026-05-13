"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, Calendar, Mail, Sparkles, TrendingUp, UserCircle } from "lucide-react";

import { ActivityHeatmap } from "@/components/charts/activity-heatmap";
import { MasteryDonut } from "@/components/charts/mastery-donut";
import { TrendChart } from "@/components/charts/trend-chart";
import { AttemptsList } from "@/components/expression/attempts-list";
import { MasterySections } from "@/components/mastery/mastery-sections";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getAccountOverview } from "@/lib/api/endpoints";

export default function AccountPage() {
  const overviewQuery = useQuery({
    queryKey: ["account-overview"],
    queryFn: getAccountOverview,
  });

  if (overviewQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  if (!overviewQuery.data) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Impossible de charger le tableau de bord.
        </CardContent>
      </Card>
    );
  }

  const { profile, mastery, activity_heatmap, quiz_progression, expression_progression } =
    overviewQuery.data;

  const quizTrend = quiz_progression.map((p) => ({ date: p.date, value: p.avg_rating }));
  const exprTrend = expression_progression.map((p) => ({
    date: p.date.slice(0, 10),
    value: p.score,
  }));

  const joined = new Date(profile.joined_at).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Tableau de bord</h1>
        <p className="mt-1 text-muted-foreground">
          Vue d&apos;ensemble de ta progression HSK.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserCircle className="h-5 w-5 text-primary" />
            Profil
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Tile icon={<Mail className="h-4 w-4" />} label="Email" value={profile.email} />
          <Tile icon={<Calendar className="h-4 w-4" />} label="Membre depuis" value={joined} />
          <Tile
            icon={<BookOpen className="h-4 w-4" />}
            label="Reviews totales"
            value={profile.total_reviews.toLocaleString("fr-FR")}
          />
          <Tile
            icon={<Sparkles className="h-4 w-4" />}
            label="Expressions corrigées"
            value={profile.total_expressions.toLocaleString("fr-FR")}
          />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Répartition de ta maîtrise</CardTitle>
            <CardDescription>État actuel de chaque mot HSK.</CardDescription>
          </CardHeader>
          <CardContent>
            <MasteryDonut data={mastery} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Activité (90 derniers jours)
            </CardTitle>
            <CardDescription>
              Intensité = nombre de mots revus chaque jour.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityHeatmap data={activity_heatmap} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Progression des quiz</CardTitle>
            <CardDescription>
              Note moyenne par jour (1 = Faux, 4 = Je connais).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={quizTrend}
              yDomain={[1, 4]}
              emptyMessage="Pas encore de session de quiz."
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Progression de l&apos;expression écrite</CardTitle>
            <CardDescription>
              Scores Claude (sur 100) sur les 30 derniers jours.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={exprTrend}
              yDomain={[0, 100]}
              emptyMessage="Pas encore de production écrite."
            />
          </CardContent>
        </Card>
      </div>

      <MasterySections />

      <AttemptsList limit={50} />
    </div>
  );
}

function Tile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-1 truncate font-medium">{value}</p>
    </div>
  );
}
