import admin from "firebase-admin";
import type { Match } from "../types/index.js";
import { removeTokens } from "./db.js";

export type SendSummary = {
  successCount: number;
  failureCount: number;
  failures: Array<{ index: number; code?: string; message: string }>;
};

let messaging: admin.messaging.Messaging | null = null;

const getMessaging = (): admin.messaging.Messaging => {
  if (messaging) return messaging;

  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) {
    throw new Error("FIREBASE_SERVICE_ACCOUNT_JSON is not set");
  }
  const serviceAccount = JSON.parse(raw) as admin.ServiceAccount;
  if (serviceAccount.private_key?.includes("\\n")) {
    serviceAccount.private_key = serviceAccount.private_key.replace(
      /\\n/g,
      "\n"
    );
  }

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
): Promise<SendSummary> => {
  if (deviceTokens.length === 0) {
    return { successCount: 0, failureCount: 0, failures: [] };
  }

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

  const response = await getMessaging().sendEachForMulticast({
    tokens: deviceTokens,
    data: dataPayload,
    webpush: {
      headers: {
        Urgency: "high"
      },
      notification: {
        title,
        body,
        tag: `match-${match.id}`,
        renotify: true,
        requireInteraction: true
      },
      fcmOptions: {
        link: "https://valorant-scoreboard.vercel.app/"
      }
    }
  });

  const failures = response.responses
    .map((item, index) => {
      if (item.success) return null;
      const error = item.error;
      return {
        index,
        code: error?.code,
        message: error?.message ?? "Unknown error"
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  const invalidTokens = failures
    .filter((failure) =>
      ["messaging/registration-token-not-registered", "messaging/invalid-registration-token"].includes(
        failure.code ?? ""
      )
    )
    .map((failure) => deviceTokens[failure.index])
    .filter(Boolean);

  if (invalidTokens.length > 0) {
    await removeTokens(invalidTokens);
  }

  return {
    successCount: response.successCount,
    failureCount: response.failureCount,
    failures
  };
};
