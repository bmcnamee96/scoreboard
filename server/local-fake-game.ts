import "dotenv/config";
import { getTokensForMatch, upsertMatches } from "./db.js";
import { sendMatchUpdate } from "./notifications.js";
import type { Match } from "../types/index.js";

const INTERVAL_MS = Number.parseInt(
  process.env.FAKE_MATCH_INTERVAL_MS ?? "30000",
  10
);
const TOTAL_DURATION_MS = Number.parseInt(
  process.env.FAKE_MATCH_DURATION_MS ?? String(45 * 60_000),
  10
);
const TOTAL_TICKS = Math.ceil(TOTAL_DURATION_MS / INTERVAL_MS);

const matchId = process.env.FAKE_MATCH_ID ?? "fake-live-test";
const notifyOnUpdate = process.env.FAKE_MATCH_NOTIFY !== "false";
const startTime = new Date().toISOString();

let scoreA = 0;
let scoreB = 0;
let tick = 0;

const makeMatch = (status: Match["status"]): Match => {
  const match: Match = {
    id: matchId,
    url: "https://www.vlr.gg/",
    teamA: "Local Alpha",
    teamB: "Local Bravo",
    scoreA,
    scoreB,
    status,
    event: "Local Dev Test",
    startTime,
    roundInfo: `Update ${tick}/${TOTAL_TICKS}`,
    updatedAt: new Date().toISOString()
  };
  return match;
};

const bumpScores = (): void => {
  if (Math.random() > 0.55) scoreA += 1;
  if (Math.random() > 0.55) scoreB += 1;
};

const runTick = async (): Promise<void> => {
  tick += 1;
  bumpScores();

  const isLast = tick >= TOTAL_TICKS;
  const status: Match["status"] = isLast ? "completed" : "live";

  await upsertMatches([makeMatch(status)]);
  console.log(
    `[fake] ${matchId} ${scoreA}-${scoreB} status=${status} (${tick}/${TOTAL_TICKS})`
  );
  if (notifyOnUpdate) {
    const tokens = await getTokensForMatch(matchId);
    if (tokens.length > 0) {
      await sendMatchUpdate(tokens, makeMatch(status));
      console.log(`[fake] notified ${tokens.length} devices`);
    }
  }

  if (isLast) {
    process.exit(0);
  }
};

console.log(
  `[fake] starting ${matchId} intervalMs=${INTERVAL_MS} ticks=${TOTAL_TICKS}`
);
void runTick();
setInterval(() => {
  void runTick();
}, INTERVAL_MS);
