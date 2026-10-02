import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-6 px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Arrakis Realty</h1>
      <p className="text-muted-foreground">
        Scaffold is running. Public site, customer app and /admin arrive in Phase 0.
      </p>
      <div>
        <Button asChild>
          <a href="/api/health">Check health</a>
        </Button>
      </div>
    </main>
  );
}
