import { useCallback, useEffect, useMemo, useState } from "react";
import type { Match } from "@shared/index";
import { requestFcmToken } from "./firebase";
import { useMatches } from "./hooks/useMatches";
import MatchCard from "./components/MatchCard";

const STORAGE_TOKEN = "scoreboard:deviceToken";
const STORAGE_FOLLOWS = "scoreboard:followedMatches";
const STORAGE_DEBUG_TOKEN = "scoreboard:debugToken";
const DEBUG_PUSH_ENABLED =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEBUG_PUSH === "true";

const loadFollowed = (): Set<string> => {
  try {
    const raw = localStorage.getItem(STORAGE_FOLLOWS);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as string[];
    return new Set(parsed);
  } catch {
    return new Set();
  }
};

const saveFollowed = (value: Set<string>): void => {
  localStorage.setItem(STORAGE_FOLLOWS, JSON.stringify([...value]));
};

export default function App(): JSX.Element {
  const { matches, loading, error, refresh } = useMatches();
  const [deviceToken, setDeviceToken] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_TOKEN)
  );
  const [followed, setFollowed] = useState<Set<string>>(() => loadFollowed());
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [debugSending, setDebugSending] = useState(false);

  useEffect(() => {
    saveFollowed(followed);
  }, [followed]);

  const sortedMatches = useMemo(() => {
    const live = matches.filter((match) => match.status === "live");
    const upcoming = matches.filter((match) => match.status !== "live");
    return [...live, ...upcoming];
  }, [matches]);

  const getDebugToken = (): string | null => {
    const cached = sessionStorage.getItem(STORAGE_DEBUG_TOKEN);
    if (cached) return cached;
    const entered = window.prompt("Enter debug token");
    if (!entered) return null;
    sessionStorage.setItem(STORAGE_DEBUG_TOKEN, entered);
    return entered;
  };

  const sendDebugPush = useCallback(async () => {
    if (!DEBUG_PUSH_ENABLED) return;
    setStatusMessage(null);
    setDebugSending(true);
    try {
      const token = getDebugToken();
      if (!token) return;

      const followedMatchId = [...followed][0];
      const matchId = followedMatchId ?? sortedMatches[0]?.id ?? "fake-live-test";
      const response = await fetch("/api/debug/push", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-debug-token": token
        },
        body: JSON.stringify({ matchId })
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setStatusMessage(
          `Debug push failed: ${payload?.error ?? response.status}`
        );
        return;
      }

      if (payload?.failureCount > 0) {
        console.warn("Debug push failures", payload.failures);
      }
      setStatusMessage(
        `Debug push sent. success=${payload?.successCount ?? 0} failure=${payload?.failureCount ?? 0}`
      );
    } finally {
      setDebugSending(false);
    }
  }, [followed, sortedMatches]);

  const ensureToken = useCallback(async (): Promise<string | null> => {
    if (deviceToken) return deviceToken;
    const token = await requestFcmToken();
    if (token) {
      localStorage.setItem(STORAGE_TOKEN, token);
      setDeviceToken(token);
    }
    return token;
  }, [deviceToken]);

  const followMatch = useCallback(
    async (match: Match) => {
      setStatusMessage(null);
      const token = await ensureToken();
      if (!token) {
        setStatusMessage(
          "Notifications are blocked. Enable them to follow a match."
        );
        return;
      }

      const response = await fetch("/api/follow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matchId: match.id, deviceToken: token })
      });

      if (!response.ok) {
        setStatusMessage("Could not follow match. Try again.");
        return;
      }

      setFollowed((prev) => new Set(prev).add(match.id));
      setStatusMessage(`Following ${match.teamA} vs ${match.teamB}.`);
    },
    [ensureToken]
  );

  const unfollowMatch = useCallback(
    async (match: Match) => {
      setStatusMessage(null);
      if (!deviceToken) return;

      const response = await fetch("/api/unfollow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matchId: match.id, deviceToken })
      });

      if (!response.ok) {
        setStatusMessage("Could not unfollow match. Try again.");
        return;
      }

      setFollowed((prev) => {
        const next = new Set(prev);
        next.delete(match.id);
        return next;
      });
      setStatusMessage(`Unfollowed ${match.teamA} vs ${match.teamB}.`);
    },
    [deviceToken]
  );

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Live Valorant</p>
          <h1>Scoreboard</h1>
          <p className="subtitle">
            Follow a match with one tap. Live scores appear as lock-screen
            notifications.
          </p>
        </div>
        <div className="hero-actions">
          {DEBUG_PUSH_ENABLED && (
            <button
              className="ghost"
              onClick={sendDebugPush}
              type="button"
              disabled={debugSending}
            >
              {debugSending ? "Sending..." : "Send Test Push"}
            </button>
          )}
          <button className="ghost" onClick={refresh} type="button">
            Refresh
          </button>
        </div>
      </header>

      {statusMessage && <div className="status">{statusMessage}</div>}
      {error && <div className="status error">{error}</div>}

      <section className="matches">
        {loading && <p className="muted">Loading matches...</p>}
        {!loading && sortedMatches.length === 0 && (
          <p className="muted">No matches found right now.</p>
        )}
        {sortedMatches.map((match) => (
          <MatchCard
            key={match.id}
            match={match}
            followed={followed.has(match.id)}
            onFollow={followMatch}
            onUnfollow={unfollowMatch}
          />
        ))}
      </section>
    </div>
  );
}
