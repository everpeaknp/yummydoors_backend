# YummyDoors Desktop Next Steps

## Current repo reality

There is no dedicated `yummydoors_desktop` repo yet.

The current sibling desktop repo is:

- `../yummy-desktop-nextjs`

That repo is the existing Yummy POS / operations Next.js desktop surface, not a YummyDoors-specific customer delivery dashboard.

## Recommended direction

Do not force YummyDoors UI into the existing POS desktop blindly.

Instead:

1. finish YummyDoors backend auth and core domain first
2. decide whether YummyDoors web surface should be:
   - a new dedicated Next.js repo, or
   - a bounded app area inside an existing repo
3. only then scaffold YummyDoors desktop/web with its own auth session flow

## Backend-first contract needed before Next.js

Before starting the YummyDoors desktop app, we should lock:

- auth response shape
- current-user payload
- restaurant-context switching model
- POS-link confirmation flow
- restaurant activation/mapping flow

## Suggested first Next.js scope after backend

- auth pages
- protected app shell
- current user bootstrap
- restaurant switcher
- linked POS account status UI
- restaurant admin overview
