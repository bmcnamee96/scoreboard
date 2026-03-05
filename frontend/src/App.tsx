import { useCallback, useEffect, useMemo, useState } from "react";
import type { Match } from "@shared/index";
import { requestFcmToken } from "./firebase";
import { useMatches } from "./hooks/useMatches";
import MatchCard from "./components/MatchCard";

const STORAGE_TOKEN = "scoreboard:deviceToken";
const STORAGE_FOLLOWS = "scoreboard:followedMatches";

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

  useEffect(() => {
    saveFollowed(followed);
  }, [followed]);

  const sortedMatches = useMemo(() => {
    const live = matches.filter((match) => match.status === "live");
    const upcoming = matches.filter((match) => match.status !== "live");
    return [...live, ...upcoming];
  }, [matches]);

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
        <button className="ghost" onClick={refresh} type="button">
          Refresh
        </button>
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
