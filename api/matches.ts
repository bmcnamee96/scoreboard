import type { VercelRequest, VercelResponse } from "@vercel/node";
import { fetchMatchesFromVlr } from "../server/vlr.js";
import { getRecentMatches, upsertMatches } from "../server/db.js";
import type { MatchesResponse } from "../types/index.js";

export default async function handler(
  _req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  try {
    const matches = await fetchMatchesFromVlr();
    if (matches.length > 0) {
      await upsertMatches(matches);
      const response: MatchesResponse = { matches };
      res.status(200).json(response);
      return;
    }

    const fallback = await getRecentMatches(40);
    res.status(200).json({ matches: fallback } satisfies MatchesResponse);
  } catch (error) {
    res
      .status(500)
      .json({ ok: false, error: (error as Error).message });
  }
}
