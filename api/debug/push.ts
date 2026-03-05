import type { VercelRequest, VercelResponse } from "@vercel/node";
import { debugPushSchema } from "../../server/validators.js";
import { readJsonBody } from "../../server/http.js";
import { getMatchesByIds, getTokensForMatch } from "../../server/db.js";
import { sendMatchUpdate } from "../../server/notifications.js";
import type { Match } from "../../types/index.js";

const makeFallbackMatch = (matchId: string): Match => ({
  id: matchId,
  url: "https://valorant-scoreboard.vercel.app/",
  teamA: "Debug Alpha",
  teamB: "Debug Bravo",
  scoreA: 1,
  scoreB: 0,
  status: "live",
  updatedAt: new Date().toISOString(),
  roundInfo: "Debug push"
});

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "Method not allowed" });
    return;
  }

  const debugToken = process.env.DEBUG_TOKEN;
  if (!debugToken) {
    res.status(404).json({ ok: false, error: "Not found" });
    return;
  }
  const provided = req.headers["x-debug-token"];
  if (typeof provided !== "string" || provided !== debugToken) {
    res.status(403).json({ ok: false, error: "Forbidden" });
    return;
  }

  try {
    const body = await readJsonBody(req);
    const parsed = debugPushSchema.safeParse(body);
    if (!parsed.success) {
      res.status(400).json({ ok: false, error: "Invalid request" });
      return;
    }

    const { matchId, deviceToken } = parsed.data;
    let tokens: string[] = [];
    let match: Match;

    if (matchId) {
      tokens = await getTokensForMatch(matchId);
      const matches = await getMatchesByIds([matchId]);
      match = matches[0] ?? makeFallbackMatch(matchId);
    } else {
      tokens = [deviceToken!];
      match = makeFallbackMatch("debug-match");
    }

    if (tokens.length === 0) {
      res.status(200).json({ ok: true, successCount: 0, failureCount: 0 });
      return;
    }

    const summary = await sendMatchUpdate(tokens, match);
    res.status(200).json({ ok: true, ...summary });
  } catch (error) {
    res
      .status(500)
      .json({ ok: false, error: (error as Error).message });
  }
}
