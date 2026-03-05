import type { VercelRequest, VercelResponse } from "@vercel/node";
import { fetchMatchesFromVlr } from "../../server/vlr.js";
import {
  getMatchesByIds,
  getSubscribedMatchIds,
  getTokensForMatch,
  upsertMatches
} from "../../server/db.js";
import { sendMatchUpdate } from "../../server/notifications.js";
import { hasScoreChanged } from "../../server/matchDiff.js";

export default async function handler(
  _req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  try {
    const subscribedMatchIds = await getSubscribedMatchIds();
    if (subscribedMatchIds.length === 0) {
      res.status(200).json({ ok: true, updated: 0 });
      return;
    }

    const latestMatches = await fetchMatchesFromVlr();
    const latestMap = new Map(latestMatches.map((match) => [match.id, match]));

    const previousMatches = await getMatchesByIds(subscribedMatchIds);
    const updates = [];

    for (const previous of previousMatches) {
      const latest = latestMap.get(previous.id);
      if (!latest) continue;
      const scoreChanged = hasScoreChanged(
        previous.scoreA,
        previous.scoreB,
        latest.scoreA,
        latest.scoreB
      );
      if (!scoreChanged && previous.status === latest.status) continue;
      updates.push(latest);
    }

    if (updates.length > 0) {
      await upsertMatches(updates);
    }

    for (const match of updates) {
      const tokens = await getTokensForMatch(match.id);
      await sendMatchUpdate(tokens, match);
    }

    res.status(200).json({ ok: true, updated: updates.length });
  } catch (error) {
    res
      .status(500)
      .json({ ok: false, error: (error as Error).message });
  }
}
