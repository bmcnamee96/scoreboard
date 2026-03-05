import { Pool } from "pg";
import type { Match, MatchStatus } from "../types/index.js";

let pool: Pool | null = null;
let schemaReady = false;

const schemaSql = `
CREATE TABLE IF NOT EXISTS matches (
  match_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  team_a TEXT NOT NULL,
  team_b TEXT NOT NULL,
  score_a INTEGER NOT NULL DEFAULT 0,
  score_b INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  event TEXT,
  start_time TEXT,
  round_info TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  match_id TEXT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
  device_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (match_id, device_token)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_match ON subscriptions(match_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_device ON subscriptions(device_token);
`;

export const getPool = (): Pool => {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL is not set");
    }
    const useSsl =
      !connectionString.includes("localhost") &&
      !connectionString.includes("127.0.0.1");
    pool = new Pool({
      connectionString,
      ssl: useSsl ? { rejectUnauthorized: false } : undefined
    });
  }
  return pool;
};

export const ensureSchema = async (): Promise<void> => {
  if (schemaReady) return;
  const client = await getPool().connect();
  try {
    await client.query(schemaSql);
    schemaReady = true;
  } finally {
    client.release();
  }
};

export const upsertMatches = async (matches: Match[]): Promise<void> => {
  if (matches.length === 0) return;
  await ensureSchema();
  const client = await getPool().connect();
  try {
    await client.query("BEGIN");
    for (const match of matches) {
      await client.query(
        `INSERT INTO matches (
          match_id, url, team_a, team_b, score_a, score_b, status, event, start_time, round_info, updated_at
        ) VALUES (
          $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW()
        )
        ON CONFLICT (match_id) DO UPDATE SET
          url = EXCLUDED.url,
          team_a = EXCLUDED.team_a,
          team_b = EXCLUDED.team_b,
          score_a = EXCLUDED.score_a,
          score_b = EXCLUDED.score_b,
          status = EXCLUDED.status,
          event = EXCLUDED.event,
          start_time = EXCLUDED.start_time,
          round_info = EXCLUDED.round_info,
          updated_at = NOW()
        `,
        [
          match.id,
          match.url,
          match.teamA,
          match.teamB,
          match.scoreA,
          match.scoreB,
          match.status,
          match.event ?? null,
          match.startTime ?? null,
          match.roundInfo ?? null
        ]
      );
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
};

export const getMatchesByIds = async (matchIds: string[]): Promise<Match[]> => {
  if (matchIds.length === 0) return [];
  await ensureSchema();
  const result = await getPool().query(
    `SELECT match_id, url, team_a, team_b, score_a, score_b, status, event, start_time, round_info, updated_at
     FROM matches WHERE match_id = ANY($1::text[])`,
    [matchIds]
  );
  return result.rows.map(mapRowToMatch);
};

export const getRecentMatches = async (limit = 50): Promise<Match[]> => {
  await ensureSchema();
  const result = await getPool().query(
    `SELECT match_id, url, team_a, team_b, score_a, score_b, status, event, start_time, round_info, updated_at
     FROM matches
     ORDER BY updated_at DESC
     LIMIT $1`,
    [limit]
  );
  return result.rows.map(mapRowToMatch);
};

export const addSubscription = async (
  matchId: string,
  deviceToken: string
): Promise<void> => {
  await ensureSchema();
  await getPool().query(
    `INSERT INTO subscriptions (match_id, device_token)
     VALUES ($1, $2)
     ON CONFLICT (match_id, device_token) DO NOTHING`,
    [matchId, deviceToken]
  );
};

export const removeSubscription = async (
  matchId: string,
  deviceToken: string
): Promise<void> => {
  await ensureSchema();
  await getPool().query(
    `DELETE FROM subscriptions WHERE match_id = $1 AND device_token = $2`,
    [matchId, deviceToken]
  );
};

export const getSubscribedMatchIds = async (): Promise<string[]> => {
  await ensureSchema();
  const result = await getPool().query(
    `SELECT DISTINCT match_id FROM subscriptions`
  );
  return result.rows.map((row) => row.match_id as string);
};

export const getTokensForMatch = async (
  matchId: string
): Promise<string[]> => {
  await ensureSchema();
  const result = await getPool().query(
    `SELECT device_token FROM subscriptions WHERE match_id = $1`,
    [matchId]
  );
  return result.rows.map((row) => row.device_token as string);
};

export const removeTokens = async (tokens: string[]): Promise<void> => {
  if (tokens.length === 0) return;
  await ensureSchema();
  await getPool().query(
    `DELETE FROM subscriptions WHERE device_token = ANY($1::text[])`,
    [tokens]
  );
};

type MatchRow = {
  match_id: string;
  url: string;
  team_a: string;
  team_b: string;
  score_a: number;
  score_b: number;
  status: string;
  event: string | null;
  start_time: string | null;
  round_info: string | null;
  updated_at: Date;
};

const mapRowToMatch = (row: MatchRow): Match => {
  const match: Match = {
    id: row.match_id,
    url: row.url,
    teamA: row.team_a,
    teamB: row.team_b,
    scoreA: Number(row.score_a),
    scoreB: Number(row.score_b),
    status: row.status as MatchStatus,
    updatedAt: row.updated_at.toISOString()
  };

  if (row.event) match.event = row.event;
  if (row.start_time) match.startTime = row.start_time;
  if (row.round_info) match.roundInfo = row.round_info;

  return match;
};
