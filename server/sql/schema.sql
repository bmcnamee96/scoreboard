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
