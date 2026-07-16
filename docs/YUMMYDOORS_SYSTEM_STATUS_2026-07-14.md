# YummyDoors System Status

**Verified date:** 2026-07-14  
**Primary backend:** `yummydoors_backend`  
**Web product:** `../yummydoors_desktop`  
**Mobile product:** `/mnt/d/Windows_Projects/yummy-user`  
**Status meaning:** `Done` means the code path exists and is wired in the referenced surface. `Partial` means only part of the intended product flow exists or consumer parity is incomplete. `Missing/Risk` means it is not a complete production capability.

## 1. Executive Summary

YummyDoors is currently a FastAPI/PostgreSQL modular backend with a shared identity model, customer ordering, merchant workspaces, restaurant catalog management, analytics, reservations, notifications, and rider dispatch. The desktop web app is the main customer and merchant web surface. The Flutter app is the customer and rider mobile surface and also contains merchant-oriented screens.

The strongest completed areas are:

- authentication, refresh sessions, roles, permissions, and workspaces
- restaurant discovery and restaurant detail/menu consumption
- merchant restaurant ownership/context switching
- category and menu-item CRUD
- carts, coupon application, fee calculation, checkout, order history, and order status actions
- merchant analytics and loyalty-related reporting
- rider invitations, private rider relationships, dispatch offers, pickup/delivery actions, GPS persistence, and realtime location events

The largest gaps are:

- payment processing and financial accounting are not a complete ledger/reconciliation system
- realtime tracking depends on active GPS publishing and frontend rebuilds; route rendering and runtime configuration still need operational verification
- desktop/mobile contract drift remains possible
- merchant and rider UI parity is uneven
- dispatch acceptance needs database-level concurrency protection before being treated as fully race-safe
- notification delivery errors are deliberately suppressed in several paths
- full POS synchronization lifecycle is not complete

## 2. Product Surfaces

### Backend: `yummydoors_backend`

The backend is the system of record for identity, restaurants, catalog, carts, orders, reviews, favorites, reservations, workspaces, merchant onboarding, analytics, notifications, and rider dispatch.

Relevant module map:

- `app/modules/auth`: registration, login, Google login, refresh, logout, password reset, profile summary, rider status/location
- `app/modules/workspaces`: workspace membership, switching, merchant applications, restaurant context
- `app/modules/restaurants`: discovery, details, restaurant profile, branches, gallery, categories linked to restaurants
- `app/modules/catalog`: menu items, categories, modifiers, merchant catalog management
- `app/modules/carts`: cart ownership, cart context, coupon application, pricing preview
- `app/modules/orders`: checkout, order history/details, merchant status actions, rider actions, order serialization
- `app/modules/rider_dispatch`: invitations, private/preferred assignments, offer creation, acceptance/rejection, expiry, dispatch policy
- `app/modules/analytics`: merchant/customer order and spend analytics
- `app/modules/notifications`: in-app notifications, web push, FCM, merchant notifications
- `app/modules/reservations`: table availability and reservation lifecycle
- `app/modules/admin`: admin catalog, restaurants, promos, reservations, onboarding/operations surfaces

### Desktop: `yummydoors_desktop`

The desktop app contains customer discovery/order surfaces, merchant onboarding and operations, merchant catalog screens, merchant analytics, merchant rider-team management, merchant order detail, and the web rider dashboard.

### Mobile: `/mnt/d/Windows_Projects/yummy-user`

The Flutter app contains customer discovery, restaurant/menu/cart/checkout, order history and tracking, reviews, profile/address flows, rider dashboard/offers/location, and merchant-oriented screens. Some merchant screens are direct API consumers and have more contract drift risk than the primary desktop merchant surface.

## 3. Identity, Roles, and Workspaces

### Current flow

1. A user registers, logs in, or authenticates through Google.
2. The backend creates or loads the user and role relationships.
3. Refresh sessions support continued authentication.
4. The account can have multiple workspaces/modes.
5. Workspace switching changes active context rather than creating a second account.
6. Merchant restaurant context is separate from the broader merchant workspace and can be switched when the merchant owns multiple restaurants.

### Roles and relationships

- customer identity is attached to the user account
- merchant access is scoped through workspace membership and restaurant assignments
- restaurant ownership is represented by `RestaurantUserAssignment` with `assignment_type = owner`
- rider access is represented by the rider role plus restaurant assignment types such as `rider_private` or `rider_preferred`
- admin/ops access is handled through role/permission checks

### Done

- unique user email/phone constraints
- refresh-session and logout flow
- role and scoped restaurant assignment model
- workspace listing and switching
- merchant application and restaurant request model
- active restaurant context for merchant operations

### Missing/Risk

- role-level coverage is not proof that all users have effective permissions; effective access must be checked through users, user roles, and role permissions
- workspace switching and frontend navigation can drift if a stale auth payload is cached
- rider/merchant mode switching is not equally polished across desktop and mobile

## 4. Restaurant Onboarding and Ownership

### Current flow

Merchant onboarding supports requests for:

- creating an external restaurant
- claiming an existing restaurant
- linking/operating a POS-linked restaurant

After approval, the merchant receives workspace/restaurant access and an owner assignment. The desktop merchant surface can select the active restaurant context.

### Done

- merchant application records
- restaurant request types
- restaurant ownership assignments
- merchant restaurant list and context switching
- restaurant profile update path

### Partial/Missing

- approval is represented in backend/admin flows, but the end-to-end operational review process needs runtime verification
- POS linking exists structurally, but full bidirectional sync, conflict handling, retries, and reconciliation are not complete
- branch-level operations and staff/team management are not a complete product workflow

## 5. Restaurant Discovery and Home Feed

### Current flow

Customer clients request restaurant/home data from the restaurant module. The feed includes location context, categories, restaurant sections, featured/promotional content, and restaurant summaries. Restaurant detail exposes restaurant metadata and menu consumption.

### Done

- customer restaurant discovery
- restaurant detail
- location-aware feed context
- featured categories and restaurant sections
- restaurant gallery and presentation fields
- desktop and mobile consumer surfaces

### Risk

- fallback behavior and serialization must be checked against the live endpoint; browser CORS-looking failures can be backend 500/serialization errors
- discovery ranking, promotion rules, and POS availability are not a single documented business-policy engine
- guest location and authenticated saved-address location have different semantics and should remain explicit

## 6. Categories and Menu Catalog

### Category model

There are global categories plus restaurant-category links. A restaurant can be linked to categories, and merchant profile responses include linked category summaries ordered by category sort order and id.

Relevant backend routes in `app/modules/catalog/api.py`:

- `GET /restaurants/{restaurant_id}/menu`
- `GET /merchant/restaurants/{restaurant_id}/categories`
- `POST /merchant/restaurants/{restaurant_id}/categories`
- `PUT /merchant/restaurants/{restaurant_id}/categories/{category_id}`
- `DELETE /merchant/restaurants/{restaurant_id}/categories/{category_id}`
- `GET /merchant/restaurants/{restaurant_id}/menu-items`
- `POST /merchant/restaurants/{restaurant_id}/menu-items`
- `PUT /merchant/restaurants/{restaurant_id}/menu-items/{item_id}`
- `DELETE /merchant/restaurants/{restaurant_id}/menu-items/{item_id}`

### Menu item model

Menu items belong to a restaurant and may reference a category. Current fields include:

- name, slug, description, image, price, currency
- availability
- food type: vegetarian, non-vegetarian, or vegan
- spicy/featured/popular flags
- rating/popularity counters
- modifier groups and modifier items

### How menu data enters the system

1. A merchant/admin creates or selects a restaurant.
2. The merchant creates global categories or links existing categories to the restaurant.
3. The merchant creates menu items under the restaurant and optionally assigns a category.
4. The merchant adds modifier groups and modifier choices where supported.
5. The merchant toggles availability and edits item data through merchant catalog endpoints.
6. Customer restaurant detail/menu endpoints read the restaurant menu and available item data.
7. Cart items snapshot menu name and price into cart/order items so historical orders are not dependent on future menu edits.

### Done

- category CRUD/linking
- menu item CRUD
- menu availability toggle
- menu modifiers in the data model
- customer menu read flow
- desktop/mobile merchant consumers exist

### Missing/Risk

- no complete audit/version history for menu price or availability changes
- slug uniqueness is indexed but not globally constrained by restaurant in the model shown
- menu item create/update authorization must remain restaurant-scoped
- modifier validation at checkout must reject unavailable or invalid selections consistently
- desktop and mobile may consume different casing/response wrappers; contract tests should cover both
- category deletion behavior and orphaned menu-item UX need explicit product rules

## 7. Cart, Pricing, Coupons, and Checkout

### Current cart flow

1. Customer gets or creates a cart for a restaurant.
2. Customer adds menu items.
3. Customer changes quantities or cart context.
4. Customer applies or removes a coupon.
5. Cart pricing is recalculated.
6. Customer submits checkout with address, payment method, cutlery/cooking/delivery instructions.
7. Backend snapshots cart contents into an order.

Relevant routes in `app/modules/carts/api.py`:

- `GET /carts`
- `GET /carts/{restaurant_id}`
- `POST /carts/{restaurant_id}/items`
- `PATCH /carts/{restaurant_id}/items/{item_id}`
- `DELETE /carts/{restaurant_id}/items/{item_id}`
- `PATCH /carts/{restaurant_id}/context`
- `POST /carts/{restaurant_id}/coupon`
- `DELETE /carts/{restaurant_id}/coupon`

Checkout is handled by `POST /orders/checkout/{cart_id}`.

### Current fee calculation

The current cart pricing code calculates:

- `items_total`: sum of item price multiplied by quantity
- coupon discount: coupon-specific discount
- delivery fee: normally `100.0`; `FREEDEL` makes it `0.0`
- service fee: `items_total * 0.05`
- tax: `items_total * 0.13`
- subtotal amount: `items_total - coupon_discount`
- total amount: `subtotal + delivery_fee + service_fee + tax_amount`, floored at zero

The order stores `coupon_discount`, `delivery_fee`, `service_fee`, `tax_amount`, `subtotal_amount`, and final `total_price`.

### Current coupon behavior

The cart service includes hard-coded coupon behavior such as `DISCOUNT50` and `FREEDEL`. This is functional starter behavior, not a complete promotion engine.

### Done

- cart ownership by customer and restaurant
- quantity updates and item deletion
- cart pricing response
- coupon apply/remove path
- order pricing snapshot at checkout
- cash/card/wallet payment method selection field

### Missing/Risk

- payment method selection is not equivalent to payment authorization or capture
- no complete gateway transaction, webhook, refund, chargeback, or reconciliation flow is visible in this backend slice
- fees are calculated in application code with fixed starter values
- no restaurant-configurable fee policy or tax jurisdiction engine
- coupon rules are hard-coded and lack usage limits, expiry, audience, stacking, and audit controls
- pricing must be revalidated transactionally at checkout to prevent stale cart values

## 8. Orders and Fulfillment

### Customer order flow

1. Checkout creates an order with a unique order number.
2. Restaurant/merchant receives the order through merchant list/websocket/notifications.
3. Merchant changes status from `placed` to `preparing`.
4. Rider dispatch begins when preparation starts.
5. Rider accepts an offer or claims an eligible open order.
6. Rider marks picked up.
7. Rider marks delivered.
8. Customer and merchant receive order updates and can view timeline data.

### Statuses

Backend order statuses include `toPay`, `placed`, `preparing`, `cancelled`, and `delivered`. Pickup is represented by `picked_up_at`, and rider assignment is represented by `rider_user_id` plus assignment timestamps/state.

### Relevant routes

- `POST /orders/summary`
- `GET /orders`
- `GET /orders/{order_id}`
- `POST /orders/checkout/{cart_id}`
- `GET /orders/merchant/me`
- `PATCH /orders/merchant/{order_id}/status`
- `GET /orders/rider/me`
- `POST /orders/rider/{order_id}/claim`
- `PATCH /orders/rider/{order_id}/picked-up`
- `PATCH /orders/rider/{order_id}/delivered`

### Done

- order item snapshots
- customer order history/detail
- merchant order list/detail
- merchant status transitions
- rider pickup and delivery transitions
- customer/merchant/rider notifications and websocket order channels
- order timeline serialization

### Missing/Risk

- merchant can still complete an order without a rider through the current status flow; this is a deliberate escape path but should be permissioned/audited
- status naming differs between backend, desktop, and mobile consumer models in places
- order state transitions need stronger server-side transition validation and idempotency
- order response contracts should be generated or contract-tested across all clients

## 9. Rider Team and Dispatch

### Invitation flow

1. Merchant invites an email for a restaurant.
2. Backend resolves an existing user when possible.
3. Rider sees the invitation in `GET /rider-dispatch/invitations/me`.
4. Rider accepts or rejects.
5. Acceptance creates a restaurant assignment: `rider_private` for private or `rider_preferred` for preferred.
6. Duplicate active/pending/accepted invitations for the same restaurant/email are rejected.
7. Self-invites are rejected.

### Private-only dispatch flow

When `restaurant.rider_dispatch_policy = private_only` and the merchant marks an order preparing:

1. Backend finds every eligible accepted private rider.
2. A pending offer is created for each private rider in the same dispatch round.
3. Every rider receives an offer notification through in-app notification, web push/FCM where configured, and rider websocket scope.
4. The first accepted offer assigns the order.
5. Other pending offers are expired.
6. A second acceptance is rejected if an order already has a rider.
7. Manual merchant assignment is rejected for `private_only` restaurants.

### Ranked/open dispatch flow

For non-private-only policy, candidates are ranked by assignment tier, distance, and id. The current path sends the next offer rather than broadcasting all open riders.

### Location flow

1. Mobile rider GPS or desktop rider browser GPS sends `PATCH /auth/me/rider-location`.
2. Backend stores latitude, longitude, and update time on the rider user.
3. For active assigned orders, backend publishes `rider_location_update` to customer and merchant realtime channels.
4. Desktop merchant/customer maps and mobile customer tracking consume the event and update the rider marker.

### Done

- private/preferred invitation and assignment model
- duplicate/self invitation validation
- private-only dispatch policy
- multi-rider private offer broadcast
- first-accept assignment behavior
- pending-offer invalidation after acceptance
- rider location persistence and realtime event publication
- desktop/mobile map marker consumers
- desktop road routing via Google Directions; mobile rider route uses road routing through OSRM

### Missing/Risk

- first-accept protection currently has application-level checks but should use a database transaction/row lock or conditional update for full concurrent race safety
- notification exceptions are suppressed in several dispatch paths; operators can miss delivery failures
- GPS freshness, consent, background tracking, battery policy, and stale marker expiry need explicit rules
- route providers differ between desktop and mobile; route parity, quotas, and fallback behavior need standardization
- rider dashboard state and merchant/customer order state still require more contract tests

## 10. Realtime and Notifications

### Realtime channels

The backend uses Redis-backed realtime channels for merchant, customer, and rider order websocket connections. Payloads are scoped by restaurant, customer, or rider user id.

### Notification channels

The notification service supports persisted in-app notifications and web push/FCM delivery paths. Order status, rider offers, invitations, and operational events use these payloads.

### Risk

Several notification sends intentionally catch broad exceptions so the main order operation succeeds. This prevents notification failure from breaking checkout/dispatch but reduces observability. A durable outbox/retry/dead-letter mechanism is still needed.

## 11. Analytics, Loyalty, and Reporting

### Current merchant analytics

Merchant analytics expose period/date-range summaries, daily points, status breakdowns, top-selling items, category breakdowns, and order/spend metrics. The desktop and mobile merchant surfaces consume analytics endpoints.

### Current customer/loyalty behavior

Completed orders can update customer loyalty totals. Customer-facing analytics are more limited than merchant analytics. Loyalty points, total spent, and order counts are present in user/order analytics code, but this is not a complete accounting or rewards ledger.

### Done

- merchant analytics endpoint and dashboard consumers
- daily/status/item/category breakdown structures
- completed-order loyalty update hook

### Missing/Risk

- no full immutable financial ledger
- no payout/commission settlement model
- no platform-fee reporting independent from delivery/service/tax fields
- refunds and reversals need explicit analytics treatment
- analytics definitions must document whether cancelled orders are included; current responses distinguish gross/net/cancelled in places but consumers can drift

## 12. Finances and Payment Reality

The system currently has **pricing fields**, not a complete finance subsystem.

### Present

- cart and order fee fields
- coupon discount
- payment method selection
- order total snapshot
- merchant/customer sales summaries
- loyalty-related totals

### Not yet a complete finance system

- payment intent/authorization/capture
- gateway webhook verification
- payment transaction table with provider ids and status history
- refunds and partial refunds
- merchant settlement/payout batches
- rider earnings and delivery compensation
- platform commission/fee ledger
- tax invoice/credit-note workflow
- reconciliation against gateway/POS/bank data
- finance permissions and close-period controls

Therefore, current “platform fee” language must not be interpreted as a settled platform commission. The verified current price components are delivery fee, service fee, tax amount, and coupon discount. Any migration to a real platform fee should add an explicit pricing/ledger model instead of reusing `service_fee` implicitly.

## 13. Reservations, Reviews, Favorites, and Promotions

### Reservations

Backend routes support restaurant table/availability and reservation lifecycle. Desktop/mobile consumers exist, but reservation parity and operational handling should be verified against the current restaurant/branch model.

### Reviews

Reviews are tied to users/orders with ownership and publication/reply fields. Review eligibility is intended to depend on completed orders.

### Favorites

Customer favorites exist for restaurants/menu items. Relationship loading and serialization must remain eager/safe to avoid endpoint failures.

### Promotions

Promo/banner and merchandising structures exist in backend/admin and customer feed surfaces. Coupon pricing remains separate from the broader merchandising/promotion model and should not be conflated.

## 14. Client Parity

### Desktop currently covers

- customer discovery, restaurant detail, menu, cart/checkout, orders
- merchant onboarding and restaurant switching
- merchant order operations
- merchant category/menu management
- merchant analytics
- merchant rider team and dispatch policy
- web rider dashboard, offers, delivery actions, GPS, and live route

### Mobile currently covers

- customer home/discovery, restaurant/menu, cart/checkout
- order history/detail/tracking
- customer realtime order websocket
- rider offers, team invitations, pickup/delivery, GPS, route map
- merchant-oriented dashboard/catalog/analytics screens

### Known parity problems

- desktop and Flutter use different response casing/wrapper assumptions in some areas
- some Flutter merchant surfaces are broad API consumers with local extraction helpers rather than typed contracts
- old desktop builds can still show manual assignment or stale status labels until rebuilt/restarted
- map providers and route behavior differ between desktop and mobile
- frontend completion must be verified visually and against live endpoints, not only by backend route existence

## 15. Current High-Priority Flaws

1. Add database-level first-accept locking/conditional update for competing rider offers.
2. Replace broad notification exception swallowing with an outbox and retry/monitoring model.
3. Define a real payment transaction and finance ledger domain before adding platform fees, payouts, or refunds.
4. Add API contract tests for desktop and Flutter payload casing, wrappers, nullability, and order status semantics.
5. Add GPS freshness/permission/background policies and stale-location UI.
6. Standardize route provider behavior and fallback between mobile and web.
7. Audit every “complete without rider” path and require explicit merchant permission/audit event.
8. Add menu/category audit/versioning and stronger modifier validation at checkout.
9. Complete POS sync lifecycle and reconciliation before treating POS-linked restaurants as operationally complete.
10. Verify production Docker migrations, Redis, workers, websocket fanout, push credentials, and Google/OSRM routing configuration separately from local development.

## 16. Recommended Next Sequence

1. Stabilize order/rider state transitions and database concurrency.
2. Add contract tests covering checkout, merchant order detail, rider offer, and location event payloads.
3. Implement notification outbox/retry and operational visibility.
4. Define payment/finance ledger requirements and schema before more fee changes.
5. Standardize live-map provider/route behavior and GPS freshness UX.
6. Close desktop/mobile catalog and merchant parity gaps.
7. Finish POS sync and production reconciliation workflows.

## 17. Verification Commands

Backend focused checks:

```bash
pytest -q
python -m compileall -q app
alembic current
```

Desktop checks:

```bash
npm run lint
npm run build
```

Mobile checks from `/mnt/d/Windows_Projects/yummy-user`:

```bash
flutter analyze
flutter test
```

If Flutter is executed from WSL, verify the Flutter installation first. A Windows Flutter SDK with CRLF shell scripts can fail under WSL with `$'\r': command not found` even when the Dart source itself is valid.

## 18. Source Map

Primary backend source areas used for this status:

- `app/modules/auth/`
- `app/modules/workspaces/`
- `app/modules/restaurants/`
- `app/modules/catalog/`
- `app/modules/carts/`
- `app/modules/orders/`
- `app/modules/rider_dispatch/`
- `app/modules/analytics/`
- `app/modules/notifications/`
- `app/modules/admin/`
- `app/modules/reservations/`
- `migrations/`

Primary client source areas used for this status:

- `../yummydoors_desktop/app/(dashboard)/merchant/`
- `../yummydoors_desktop/app/(dashboard)/rider/`
- `/mnt/d/Windows_Projects/yummy-user/lib/features/orders/`
- `/mnt/d/Windows_Projects/yummy-user/lib/features/rider/`
- `/mnt/d/Windows_Projects/yummy-user/lib/features/merchant/`
