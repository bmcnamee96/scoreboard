import { useCallback, useEffect, useState } from "react";
import type { Match, MatchesResponse } from "@shared/index";

export const useMatches = (): {
  matches: Match[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
} => {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMatches = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch("/api/matches", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load matches");
      }
      const payload = (await response.json()) as MatchesResponse;
      setMatches(payload.matches ?? []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMatches();
    const interval = window.setInterval(fetchMatches, 30000);
    return () => window.clearInterval(interval);
  }, [fetchMatches]);

  return { matches, loading, error, refresh: fetchMatches };
};
