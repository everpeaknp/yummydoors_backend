# YummyDoors Backend API Reference

This is the current backend API surface that should match what Swagger exposes
at `/docs` and `/openapi.json`.

## Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/auth/me`

## Customer Profile

- `GET /api/v1/me/profile`
- `PATCH /api/v1/me/profile`
- `GET /api/v1/me/addresses`
- `POST /api/v1/me/addresses`
- `PATCH /api/v1/me/addresses/{address_id}`
- `DELETE /api/v1/me/addresses/{address_id}`
- `POST /api/v1/me/addresses/{address_id}/default`

## Discovery And Restaurants

- `GET /api/v1/home/feed`
- `GET /api/v1/restaurants`
- `GET /api/v1/restaurants/{slug}`
- `GET /api/v1/search`
- `GET /api/v1/restaurants/{slug}/reviews`

Important note:

- Search currently lives at `GET /api/v1/search`, not `GET /api/v1/restaurants/search`.

## Carts

- `GET /api/v1/carts`
- `GET /api/v1/carts/{restaurant_id}`
- `POST /api/v1/carts/{restaurant_id}/items`
- `PATCH /api/v1/carts/{restaurant_id}/items/{item_id}`
- `DELETE /api/v1/carts/{restaurant_id}/items/{item_id}`
- `PATCH /api/v1/carts/{restaurant_id}/context`
- `POST /api/v1/carts/{restaurant_id}/coupon`
- `DELETE /api/v1/carts/{restaurant_id}/coupon`

## Orders

- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `POST /api/v1/orders/checkout/{cart_id}`

## Reservations

- `GET /api/v1/restaurants/{slug}/reservations/availability`
- `POST /api/v1/restaurants/{slug}/reservations`
- `GET /api/v1/reservations`
- `GET /api/v1/reservations/{reservation_id}`
- `POST /api/v1/reservations/{reservation_id}/cancel`

## Merchant And Workspace

- merchant application flow
- restaurant claim/create request flow
- workspace switching flow

These are already mounted in Swagger and remain part of the backend surface.

## Admin

- admin restaurant CRUD
- admin category CRUD
- admin menu item CRUD
- admin promo CRUD
- admin merchant approval flow

## What This Means Product-Wise

The backend is already beyond auth-only status.

It now has live API domains for:

- auth
- customer profile and addresses
- restaurant discovery
- restaurant detail and reviews
- carts
- orders
- reservations
- merchant onboarding
- admin ingestion

Still not complete yet:

- wishlist / favorites
- full coupon rule engine
- payment gateway integration
- live rider tracking
- merchant/admin UI coverage for every new metadata field
