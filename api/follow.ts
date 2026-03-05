import type { VercelRequest, VercelResponse } from "@vercel/node";
import { addSubscription, upsertMatches } from "../server/db.js";
import { readJsonBody } from "../server/http.js";
import { followRequestSchema } from "../server/validators.js";
import { fetchMatchesFromVlr } from "../server/vlr.js";
import type { FollowResponse } from "../types/index.js";

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "Method not allowed" });
    return;
  }

  try {
    const body = await readJsonBody(req);
    const parsed = followRequestSchema.safeParse(body);
    if (!parsed.success) {
      res.status(400).json({ ok: false, error: "Invalid request" });
      return;
    }

    const { matchId, deviceToken } = parsed.data;

    const matches = await fetchMatchesFromVlr();
    const match = matches.find((item) => item.id === matchId);
    await upsertMatches([
      match ?? {
        id: matchId,
        url: `https://www.vlr.gg/${matchId}/`,
        teamA: "TBD",
        teamB: "TBD",
        scoreA: 0,
        scoreB: 0,
        status: "scheduled",
        updatedAt: new Date().toISOString()
      }
    ]);

    await addSubscription(matchId, deviceToken);

    const response: FollowResponse = { ok: true };
    res.status(200).json(response);
  } catch (error) {
    res
      .status(500)
      .json({ ok: false, error: (error as Error).message });
  }
}
