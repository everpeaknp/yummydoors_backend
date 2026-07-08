# API And Auth Notes

## Auth Shape

Core auth routes live under `/api/v1/auth`.

Important routes:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/admin/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

Admin console should use `POST /auth/admin/login`, not the standard customer login route.

## Customer Address Persistence

Address sync is not purely client-side.

Backend address routes:

- `GET /me/addresses`
- `POST /me/addresses`
- `PATCH /me/addresses/{address_id}`
- `DELETE /me/addresses/{address_id}`
- `POST /me/addresses/{address_id}/default`

Desktop homepage location flow only persists to backend when:

- user is logged in
- user has a phone number on profile

Otherwise the chosen location stays only in browser state.

## Contract Source Of Truth

When frontend behavior is suspicious, verify:

1. route exists in `app/modules/*/api.py`
2. response schema exists in `schemas.py`
3. service actually populates the fields the frontend expects
