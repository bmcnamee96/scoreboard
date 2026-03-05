export type MatchStatus = "scheduled" | "live" | "completed";

export type Match = {
  id: string;
  url: string;
  teamA: string;
  teamB: string;
  scoreA: number;
  scoreB: number;
  status: MatchStatus;
  event?: string;
  startTime?: string;
  roundInfo?: string;
  updatedAt: string;
};

export type Subscription = {
  matchId: string;
  deviceToken: string;
  createdAt: string;
};

export type MatchesResponse = {
  matches: Match[];
};

export type FollowRequest = {
  matchId: string;
  deviceToken: string;
};

export type UnfollowRequest = {
  matchId: string;
  deviceToken: string;
};

export type FollowResponse = {
  ok: true;
};

export type ApiError = {
  ok: false;
  error: string;
};
