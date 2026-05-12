"use client";

import { PencilLine } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ExpressionPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PencilLine className="h-5 w-5 text-primary" />
          Expression écrite
        </CardTitle>
        <CardDescription>
          Cette section arrive dans le Bloc 4. Elle proposera des sujets HSK + correction
          structurée par Claude avec streaming SSE.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        En attendant, l&apos;ancienne version Streamlit reste accessible.
      </CardContent>
    </Card>
  );
}
