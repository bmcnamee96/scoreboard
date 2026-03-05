import type { VercelRequest, VercelResponse } from "@vercel/node";
import { fetchMatchesFromVlr } from "../server/vlr.js";
import { getRecentMatches, upsertMatches } from "../server/db.js";
import type { MatchesResponse } from "../types/index.js";

const includeDevMatches = (): boolean =>
  process.env.DEV_FAKE_MATCHES === "true";

export default async function handler(
  _req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  try {
    const matches = await fetchMatchesFromVlr();
    const devMatches = includeDevMatches()
      ? (await getRecentMatches(20)).filter((match) =>
          match.id.startsWith("fake-")
        )
      : [];
    if (matches.length > 0) {
      await upsertMatches([...matches, ...devMatches]);
      const merged = [...matches];
      for (const devMatch of devMatches) {
        if (!merged.find((item) => item.id === devMatch.id)) {
          merged.push(devMatch);
        }
      }
      const response: MatchesResponse = { matches };
      res.status(200).json({ matches: merged });
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
