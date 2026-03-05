import type { Match } from "@shared/index";

type Props = {
  match: Match;
  followed: boolean;
  onFollow: (match: Match) => void;
  onUnfollow: (match: Match) => void;
};

const statusLabel = (status: Match["status"]): string => {
  if (status === "live") return "LIVE";
  if (status === "completed") return "FINAL";
  return "UPCOMING";
};

export default function MatchCard({
  match,
  followed,
  onFollow,
  onUnfollow
}: Props): JSX.Element {
  return (
    <article className={`match-card ${match.status}`}>
      <div className="match-header">
        <span className={`pill ${match.status}`}>{statusLabel(match.status)}</span>
        {match.event && <span className="event">{match.event}</span>}
      </div>

      <div className="teams">
        <div className="team">
          <span className="team-name">{match.teamA}</span>
          <span className="team-score">{match.scoreA}</span>
        </div>
        <div className="team">
          <span className="team-name">{match.teamB}</span>
          <span className="team-score">{match.scoreB}</span>
        </div>
      </div>

      <div className="meta">
        {match.startTime && <span>{match.startTime}</span>}
        {match.roundInfo && <span>{match.roundInfo}</span>}
      </div>

      <div className="actions">
        <a
          className="link"
          href={match.url}
          target="_blank"
          rel="noreferrer"
        >
          Open on VLR
        </a>
        {followed ? (
          <button
            className="secondary"
            type="button"
            onClick={() => onUnfollow(match)}
          >
            Unfollow
          </button>
        ) : (
          <button
            className="primary"
            type="button"
            onClick={() => onFollow(match)}
          >
            Follow
          </button>
        )}
      </div>
    </article>
  );
}
