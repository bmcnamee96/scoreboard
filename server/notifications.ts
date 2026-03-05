import admin from "firebase-admin";
import type { Match } from "../types/index.js";

let messaging: admin.messaging.Messaging | null = null;

const getMessaging = (): admin.messaging.Messaging => {
  if (messaging) return messaging;

  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) {
    throw new Error("FIREBASE_SERVICE_ACCOUNT_JSON is not set");
  }
  const serviceAccount = JSON.parse(raw) as admin.ServiceAccount;

  if (!admin.apps.length) {
    admin.initializeApp({
      credential: admin.credential.cert(serviceAccount)
    });
  }

  messaging = admin.messaging();
  return messaging;
};

export const sendMatchUpdate = async (
  deviceTokens: string[],
  match: Match
): Promise<void> => {
  if (deviceTokens.length === 0) return;

  const title = `${match.teamA} vs ${match.teamB}`;
  const body = `${match.scoreA}-${match.scoreB} · ${match.status.toUpperCase()}`;

  const dataPayload: Record<string, string> = {
    matchId: match.id,
    title,
    body,
    scoreA: String(match.scoreA),
    scoreB: String(match.scoreB),
    status: match.status,
    url: "/",
    tag: `match-${match.id}`
  };

  await getMessaging().sendEachForMulticast({
    tokens: deviceTokens,
    data: dataPayload,
    webpush: {
      headers: {
        Urgency: "high"
      }
    }
  });
};
