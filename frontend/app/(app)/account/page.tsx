"use client";

import { UserCircle } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth/auth-context";

export default function AccountPage() {
  const { user } = useAuth();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserCircle className="h-5 w-5 text-primary" />
          Mon compte
        </CardTitle>
        <CardDescription>
          Connecté en tant que <strong>{user?.email}</strong>.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Le dashboard complet (stats de progression FSRS, historique des expressions
        écrites, gestion du compte) arrive dans le Bloc 4.
      </CardContent>
    </Card>
  );
}
