import * as cheerio from "cheerio";
import type { Match, MatchStatus } from "../types/index.js";

const BASE_URL = "https://www.vlr.gg";
const MATCHES_URL = `${BASE_URL}/matches`;

const cleanText = (text: string): string =>
  text.replace(/\s+/g, " ").trim();

const toScore = (text: string): number => {
  const value = Number.parseInt(text, 10);
  return Number.isFinite(value) ? value : 0;
};

const parseStatus = (raw: string, classes: string): MatchStatus => {
  const normalized = raw.toLowerCase();
  if (classes.includes("mod-live") || normalized.includes("live")) {
    return "live";
  }
  if (normalized.includes("final") || normalized.includes("complete")) {
    return "completed";
  }
  return "scheduled";
};

export const fetchMatchesFromVlr = async (): Promise<Match[]> => {
  const response = await fetch(MATCHES_URL, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (compatible; ScoreboardBot/1.0; +https://vercel.app)"
    }
  });

  if (!response.ok) {
    throw new Error(`VLR request failed: ${response.status}`);
  }

  const html = await response.text();
  const $ = cheerio.load(html);
  const matches: Match[] = [];

  $("a.match-item, .wf-module-item.match-item a, .wf-module-item a.match-item").each(
    (_, element) => {
      const node = $(element);
      const href = node.attr("href") ?? "";
      const idMatch = href.match(/\/(\d+)\//);
      const matchId = idMatch?.[1];
      if (!matchId) return;

      const teamNodes = node.find(".match-item-vs-team");
      const teamA = cleanText(teamNodes.first().find(".match-item-vs-team-name").text() || teamNodes.first().text());
      const teamB = cleanText(teamNodes.last().find(".match-item-vs-team-name").text() || teamNodes.last().text());

      const scoreNodes = node.find(".match-item-vs-team-score");
      const scoreA = toScore(scoreNodes.first().text());
      const scoreB = toScore(scoreNodes.last().text());

      const statusText = cleanText(node.find(".match-item-status").text());
      const status = parseStatus(statusText, node.attr("class") ?? "");

      const event = cleanText(
        node.find(".match-item-event, .match-item-event-series").first().text()
      );
      const startTime = cleanText(node.find(".match-item-time").text());
      const roundInfo = cleanText(node.find(".match-item-round").text());

      const match: Match = {
        id: matchId,
        url: `${BASE_URL}${href}`,
        teamA: teamA || "TBD",
        teamB: teamB || "TBD",
        scoreA,
        scoreB,
        status,
        updatedAt: new Date().toISOString()
      };

      if (event) match.event = event;
      if (startTime) match.startTime = startTime;
      if (roundInfo) match.roundInfo = roundInfo;

      matches.push(match);
    }
  );

  return matches;
};
