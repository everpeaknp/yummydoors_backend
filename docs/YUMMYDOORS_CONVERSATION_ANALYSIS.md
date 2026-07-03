# YummyDoors Conversation Analysis

## Purpose

This document separates:

- what is directly supported by the existing shared conversation and current repo artifacts
- what is implied by the mobile product surface
- what still remains an engineering inference and should be validated before implementation

It is meant to stop us from building the backend on vague assumptions.

## Sources Reviewed

### Shared conversation

Shared link reviewed:

- `https://chatgpt.com/share/6a452f1b-27b0-83e8-9d5c-afb0c6eb5b17`

Notes:

- The public share page is heavily serialized, so the full transcript was not available as a clean plain-text conversation export.
- The page title is `Sprint 1`.
- The page content still exposes enough readable fragments to recover the main technical decisions and planning direction.

### Backend repo

- [YUMMYDOORS_TECH_SUMMARY.md](/home/ramon/projects/everacy/yummydoors_backend/YUMMYDOORS_TECH_SUMMARY.md)

### Mobile repo

Sibling repo inspected:

- `../yummydoors_mobile`

Key files reviewed:

- `lib/Routes/app_router.dart`
- `lib/Routes/app_routes.dart`
- `lib/core/di/injection.dart`
- `lib/core/network/api_constants.dart`
- `lib/features/home/data/repositories/home_repository_mock.dart`
- `lib/features/home/domain/entities/*`
- `lib/features/home/presentation/pages/*`
- `lib/features/cart/presentation/pages/*`
- `lib/features/orders/presentation/pages/*`
- `lib/features/profile/presentation/pages/*`
- `lib/features/restro/presentation/pages/restro_page.dart`

## What The Conversation Clearly Confirms

These points are directly supported by the shared conversation fragments and the existing backend summary file.

### Product split

YummyDoors is intended to be a separate product surface, not just a feature inside the existing Yummy POS backend.

Confirmed split:

- customer app in `Flutter`
- restaurant/admin web panel in `Next.js`
- separate YummyDoors backend
- separate existing POS backend
- API-only communication between YummyDoors and POS

### Core backend architecture direction

The agreed backend direction is:

- `FastAPI`
- `PostgreSQL`
- `Redis`
- `Celery`
- `WebSockets`
- modular monolith first, not microservices first

This is consistent across:

- the shared conversation fragments
- the current `YUMMYDOORS_TECH_SUMMARY.md`

### Supporting platform choices

The conversation also clearly points to:

- Firebase Auth
- Firebase Notifications
- JWT-based backend session/authorization handling where needed
- Cloudinary or object storage for media
- a payment gateway layer
- MapLibre/OpenStreetMap direction instead of starting Google-first

### Business model direction

The strongest business/architecture insight from the shared conversation is this:

- YummyDoors must support both `Yummy Partner` restaurants and `external` restaurants
- Yummy Partner restaurants use the POS as the restaurant-side operational source of truth
- external restaurants are managed directly by YummyDoors

That means the backend cannot be designed as a simple single-path food ordering app.

It must support dual order ownership:

- POS-owned restaurant operations for partner restaurants
- YummyDoors-owned restaurant operations for external restaurants

### Important operational implications confirmed in the conversation

The conversation fragments explicitly point toward:

- order tracking
- delivery orchestration
- dashboard/admin systems
- payment callback handling
- restaurant media
- promotion and offer handling
- migration path from external restaurant to POS-connected partner restaurant

## What The Mobile Repo Clearly Confirms

The mobile repo is mostly presentation-layer and mocked, but it still tells us a lot about the intended product.

### Confirmed user-facing modules

Based on routes and pages, the customer app currently expects these product areas:

- home feed
- restaurant listing/discovery
- restaurant detail
- menu browsing
- item detail and customization UI
- cart
- delivery address management
- order summary and payment selection
- order history
- order overview
- order tracking
- restaurant reviews
- search
- profile
- book table
- select table
- reservation success

### Confirmed service-mode concept

The restaurant detail UI includes multiple modes:

- delivery
- pickup
- book table
- order for later

This is a major backend requirement, not just UI decoration.

### Confirmed payment expectations

The order summary UI shows payment options for:

- credit/debit card
- IME Pay
- Esewa
- cash on delivery

Even if exact providers change later, the backend must be built around a general payment method abstraction.

### Confirmed reservation expectations

The booking flow expects:

- guest count
- visit date
- visit time
- table category
- table availability/selection
- reservation confirmation data

That means table booking is not a trivial note field. It needs its own domain model.

### Confirmed address expectations

The cart and address pages imply:

- multiple saved addresses
- selected delivery address per order/cart
- recipient details
- phone number
- email
- street-level address storage

### Confirmed review expectations

The review UI implies:

- restaurant rating summary
- individual reviews
- photo attachments
- leave-a-review flow

This should be modeled as a first-class reviews subsystem, ideally tied to completed orders.

## What The Mobile Repo Does Not Confirm

The mobile repo should not be mistaken for a backend contract.

Important limitations:

- the home feed is still served by `HomeRepositoryMock`
- `ApiConstants.baseUrl` is still `https://example.com`
- dependency injection wires mock repositories, not live API repositories
- many screens are hardcoded from Figma-like placeholders
- order state, tables, search data, and payment methods are mostly presentation mocks

So the mobile repo confirms product intent, but not final backend payload design.

## What We Have Today

### In `yummydoors_backend`

Current reality:

- there is no backend implementation yet
- there is no API layer yet
- there is no database schema yet
- there is no migrations setup yet
- there is no repository structure yet
- there is no deployment setup yet
- there is only a high-level summary document

### In `yummydoors_mobile`

Current reality:

- there is a substantial UI prototype
- there is route structure for major customer flows
- there are local state models and cubits
- there is almost no real backend integration yet
- there is enough product surface to derive a serious backend design

## What Must Be Treated As Firm vs Soft

### Firm enough to design around now

- separate YummyDoors backend
- modular monolith architecture
- POS integration over APIs
- dual restaurant model: partner vs external
- customer app + restaurant/admin panel + backend split
- PostgreSQL + Redis + Celery + WebSockets direction
- customer flows for browse, cart, order, tracking, payment, address, reviews, reservation

### Soft and should be validated before hard-coding

- exact payment providers beyond generic wallet/card/COD support
- whether book table launches in MVP or phase 2
- whether order-for-later is real for MVP
- whether rider management is first-party or only internal ops
- exact restaurant dashboard scope in phase 1
- exact Firebase responsibility split versus backend-owned tokens/sessions
- exact boundaries between POS-owned and YummyDoors-owned order statuses

## Practical Conclusion

The conversation plus the mobile app together are enough to do proper backend planning now.

But the correct conclusion is not:

- "the backend requirements are already fully specified"

The correct conclusion is:

- "the ecosystem and domain boundaries are now clear enough to design the backend properly from the beginning"

That means the next step is not coding random endpoints.

The next step is:

- define the domain model
- define module boundaries
- define the database shape
- define the dual order-ownership model
- define the phased implementation plan

That is captured in:

- [YUMMYDOORS_SYSTEM_BLUEPRINT.md](/home/ramon/projects/everacy/yummydoors_backend/docs/YUMMYDOORS_SYSTEM_BLUEPRINT.md)
