# Codex Task: Lightweight Valorant Match Follower with Live Notifications

## Project Overview
We are building a lightweight web-based tool that allows users to follow live Valorant matches sourced from VLR.gg and receive real-time notifications directly on their mobile device lock screen. The goal is a simple, no-login, minimal-setup experience where users can quickly follow a match and receive live score updates as persistent notifications.

## Key Features
- Web-Based Interface: Users visit a simple web app (hosted on Vercel) where they can see a list of upcoming and live matches.
- Follow Match with One Tap: Users tap a "follow" button on a match; this registers their device for notifications for that specific match.
- Live Notifications: As the match progresses, a persistent notification (live activity on iOS, ongoing notification on Android) will remain on the user's lock screen and update in real time with the current score and round information.
- No User Account Needed: The experience is designed to be frictionless. Users do not have to log in. They simply allow notifications once and tap to follow a match.

## Technical Stack
- Frontend & Hosting: Vercel for both the static web frontend and serverless backend functions.
- Backend: Vercel serverless functions to handle follow requests, poll VLR.gg for match updates, and send notifications.
- Database: Minimal database (e.g., free-tier PostgreSQL on a service like Supabase or Neon) to store which matches are being followed and by which devices.
- Push Notifications: Use a free push service like Firebase Cloud Messaging (FCM) to send the notifications.

## Data Model
- Matches Table: Stores match IDs and basic match info (like teams and status).
- Subscriptions Table: Stores which device token is subscribed to which match, so we know who to notify.

## TypeScript and Type Safety
- Strict TypeScript Config: Use a strict tsconfig.json to enforce no implicit any, exact optional property types, and other strict type rules.
- Centralized Types: Define all domain types (e.g., Match, Subscription) in a single TypeScript types file to keep things clean and prevent duplication.
- Schema-Driven Validation: Use a library like Zod to validate external data and ensure that our internal types always match the validated schema.

---

# Agents.md - Project Index and Structure Guide

## Overview
This document serves as the index and backbone structure for the entire project. It outlines the core organization of our site's codebase - both frontend and backend - and establishes how we maintain TypeScript standards and update indexing as the project evolves.

## Code Structure
- Frontend: All frontend code is housed under the /frontend directory. This includes all React components, pages, styles, and the Firebase service worker under /frontend/public. We maintain a consistent folder structure to keep components organized by feature or section.
- Backend: Backend logic is implemented via Vercel serverless functions under /api. Shared server logic (DB, scraping, notifications, validation) lives under /server. Each API route is defined as a separate function file, making it easy to maintain and scale.
- Local Dev API: A local API runner is available at /server/local-api.ts for development without Vercel routing.
- Types: Shared types are defined under /types for use by both frontend and backend.
- Tests: Unit tests live under /tests and are executed with Vitest.
- Config: Project-wide config lives at the repo root (package.json, tsconfig.json, tsconfig.test.json, vitest.config.ts, .env.example, .gitignore, README.md).

## TypeScript Standards
- Strict Typing: We enforce strict TypeScript rules project-wide. Our tsconfig.json is set to eliminate implicit any, enforce strict null checks, and ensure all types are well-defined.
- Centralized Types: All shared types and interfaces are defined in a single /types directory. This ensures consistency and reusability across the codebase.

## Indexing and Maintenance
- Code Indexing: This document acts as the master index of the project structure. Whenever the site structure changes - like adding new major sections or reorganizing directories - this file should be updated accordingly.
- Excluding Feature Details: This index focuses solely on the site's backbone and TypeScript standards. Feature-specific details are documented separately so this file remains stable over time.
