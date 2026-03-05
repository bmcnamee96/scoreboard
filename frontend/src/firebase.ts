import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported as analyticsSupported } from "firebase/analytics";
import { getMessaging, getToken, isSupported } from "firebase/messaging";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

let appInitialized = false;

const initApp = async (): Promise<void> => {
  if (appInitialized) return;
  const app = initializeApp(firebaseConfig);
  if (await analyticsSupported()) {
    getAnalytics(app);
  }
  appInitialized = true;
};

export const requestFcmToken = async (): Promise<string | null> => {
  if (!(await isSupported())) return null;

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  await initApp();
  const messaging = getMessaging();
  const registration = await navigator.serviceWorker.register(
    "/firebase-messaging-sw.js"
  );

  const vapidKey = import.meta.env.VITE_FCM_VAPID_KEY;
  if (!vapidKey) return null;

  const token = await getToken(messaging, {
    vapidKey,
    serviceWorkerRegistration: registration
  });

  return token || null;
};
