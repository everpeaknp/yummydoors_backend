# Current State

Backend is no longer just a scaffold. It already contains:

- local auth and refresh token flow
- dedicated admin login flow
- customer profile and address APIs
- restaurant discovery and detail APIs
- favorites APIs
- review ownership / write flow support
- cart and order starter flows
- reservation APIs
- merchant applications and workspaces
- admin category / restaurant / promo / reservation surfaces

Known reality:

- some frontend surfaces still lag the backend contract
- Swagger may be ahead of desktop/admin wiring
- production deploy uses Docker on VPS and must be verified separately from local

When asked "what is left", compare backend route existence with:

- `../yummydoors_desktop`
- `../yummydoors_admin`
- Flutter mock flows in `../yummydoors_mobile`
