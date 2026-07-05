# YummyDoors Backend Gaps From Flutter

This document treats `yummydoors_mobile` as a product-shape reference, not as a backend truth source.

The Flutter app is still heavily hardcoded, but its screens clearly show what the real YummyDoors backend must eventually support.

This is the practical question:

- not "what does Flutter already implement?"
- but "what backend domains, tables, and endpoints do we need so those screens can become real?"

## Verified Source Surfaces

Flutter files reviewed:

- `lib/features/home/presentation/pages/home_page.dart`
- `lib/features/home/presentation/widgets/home_app_bar.dart`
- `lib/features/home/presentation/widgets/category_strip.dart`
- `lib/features/home/presentation/widgets/promo_carousel.dart`
- `lib/features/home/presentation/widgets/promo_banner_carousel.dart`
- `lib/features/home/presentation/widgets/restaurant_card.dart`
- `lib/features/home/presentation/widgets/recommended_food_card.dart`
- `lib/features/home/presentation/widgets/popular_food_card.dart`
- `lib/features/home/presentation/pages/restaurant_detail_page.dart`
- `lib/features/restro/presentation/pages/restro_page.dart`
- `lib/features/profile/presentation/pages/profile_page.dart`
- `lib/features/profile/presentation/widgets/edit_profile_form.dart`
- `lib/features/cart/presentation/pages/add_delivery_address_page.dart`
- `lib/features/cart/presentation/pages/cart_detail_page.dart`
- `lib/features/orders/presentation/pages/orders_page.dart`

Backend files reviewed:

- `app/modules/auth/api.py`
- `app/modules/auth/service.py`
- `app/modules/customers/api.py`
- `app/modules/restaurants/api.py`
- `app/modules/restaurants/schemas.py`
- `app/modules/catalog/api.py`
- `app/modules/catalog/schemas.py`
- `app/modules/merchandising/api.py`
- `app/modules/merchandising/schemas.py`
- `app/modules/workspaces/api.py`
- `app/modules/admin/api.py`

## What Backend Already Covers Well

These foundations already exist and are correctly moving in the right direction:

- auth and session lifecycle
  - register
  - login
  - Google login
  - refresh rotation
  - logout
  - password reset
  - audit logging
  - rate limiting
- customer identity
  - profile read/update
  - saved addresses
  - default address
- homepage discovery foundation
  - `GET /api/v1/home/feed`
  - `GET /api/v1/restaurants`
  - promos
  - recommended items
  - popular foods
- menu/catalog foundation
  - menu items
  - modifier groups
  - modifier items
- merchant/account expansion foundation
  - workspaces
  - merchant applications
  - restaurant claim / create / POS-link requests
  - admin approval flow
- admin ingestion foundation
  - restaurants CRUD
  - categories CRUD
  - menu item CRUD
  - promo CRUD

So the backend is not weak.

It is already a solid:

- identity backend
- customer profile backend
- homepage/discovery backend
- merchant onboarding backend

What it is not yet is a full customer commerce backend.

## Core Insight From Flutter

The mobile app implies that YummyDoors is not only:

- discover restaurants
- show promos
- manage account

It also implies:

- deep restaurant detail
- real cart behavior
- checkout behavior
- customer orders
- saved preferences
- favorites
- notifications
- optional dine-in / table booking flows

That means our backend still lacks the full transactional side of the product.

## Missing Backend Domains

### 1. Restaurant Detail Domain

Flutter has a large restaurant detail screen.

That page implies a real backend contract for:

- restaurant hero
- logo
- cover image
- open / closed state
- rating summary
- cuisine
- ETA
- distance
- delivery / pickup / book table / order later modes
- restaurant-specific recommended items
- restaurant menu sections
- restaurant category tabs
- restaurant detail tab content
- review summary

Current backend status:

- `GET /restaurants` exists
- `GET /restaurants/{restaurant_id}/menu` exists
- full restaurant detail endpoint does not exist yet

Needed endpoint:

- `GET /api/v1/restaurants/{slug}`
  - or `GET /api/v1/restaurants/{id}/detail`

Recommended response shape:

- restaurant summary block
- service modes block
- menu categories block
- grouped menu sections block
- recommended items block
- reviews summary block
- optional booking capability block

### 2. Category Filtering and Browse Domain

Flutter category strip is interactive.

That means the backend needs more than just "send categories once".

Needed behavior:

- browse restaurants by category
- potentially combine category with location and filters
- support "all" category properly

Current backend status:

- home feed returns categories
- restaurants list exists
- no clear category-filtered restaurant endpoint contract yet

Needed endpoint options:

- `GET /api/v1/restaurants?category_slug=momo`
- `GET /api/v1/home/feed?category_slug=momo`

Recommended direction:

- keep `home/feed` for homepage composition
- use `restaurants` for browse filtering and pagination

### 3. Search Domain

Flutter has search entry points and search state.

Needed backend capabilities:

- search restaurants
- search menu items
- search suggestions
- recent searches or popular searches later

Current backend status:

- no proper public search API yet

Needed endpoints:

- `GET /api/v1/search?q=...`
- `GET /api/v1/search/suggestions?q=...`

Recommended search result blocks:

- restaurants
- menu_items
- categories
- suggested_terms

### 4. Cart Domain

Flutter cart detail flow implies a real cart system.

Needed data/features:

- active cart per user
- cart restaurant context
- cart items
- quantity changes
- modifier selections
- cooking requests / special instructions
- "no cutlery" flag
- out-of-stock handling
- add more items
- item replacement / similar suggestions later

Current backend status:

- no cart module exists yet

Needed tables:

- `carts`
- `cart_items`
- `cart_item_modifier_selections`
- maybe `cart_item_notes`

Recommended fields:

`carts`

- `id`
- `user_id`
- `restaurant_id`
- `status`
- `delivery_address_id`
- `special_instructions`
- `no_cutlery`
- `coupon_code`
- `subtotal_amount`
- `discount_amount`
- `delivery_fee_amount`
- `tax_amount`
- `total_amount`
- timestamps

`cart_items`

- `id`
- `cart_id`
- `menu_item_id`
- `quantity`
- `unit_price`
- `total_price`
- `special_request`
- `snapshot_name`
- `snapshot_image_url`
- `availability_status`
- timestamps

`cart_item_modifier_selections`

- `id`
- `cart_item_id`
- `modifier_group_id`
- `modifier_item_id`
- `price_adjustment`

Needed endpoints:

- `GET /api/v1/cart`
- `POST /api/v1/cart/items`
- `PATCH /api/v1/cart/items/{item_id}`
- `DELETE /api/v1/cart/items/{item_id}`
- `PATCH /api/v1/cart`
- `POST /api/v1/cart/apply-coupon`

### 5. Checkout Domain

Flutter cart flow implies checkout pricing and final submission.

Needed capabilities:

- selected address
- fee calculation
- discount application
- coupon validation
- payment method selection
- place order

Current backend status:

- no checkout domain exists yet

Needed tables or service layer concepts:

- `checkout_sessions` or checkout service logic
- pricing calculator
- coupon validation service
- payment intent or payment method reference

Needed endpoints:

- `POST /api/v1/checkout/preview`
- `POST /api/v1/checkout/place-order`

Preview should return:

- subtotal
- delivery fee
- tax/service fee
- discount
- total
- unavailable items
- address snapshot

### 6. Orders Domain

Flutter has an orders section and order states.

Needed backend features:

- order creation
- list my orders
- order detail
- order status timeline
- reorder
- cancellation rules

Current backend status:

- no customer orders module exists yet

Needed tables:

- `orders`
- `order_items`
- `order_item_modifier_selections`
- `order_status_events`
- maybe `order_payments`

Recommended `orders` fields:

- `id`
- `user_id`
- `restaurant_id`
- `delivery_address_id`
- `order_number`
- `status`
- `fulfillment_type`
- `payment_status`
- `subtotal_amount`
- `discount_amount`
- `delivery_fee_amount`
- `tax_amount`
- `total_amount`
- `special_instructions`
- `no_cutlery`
- timestamps

Needed endpoints:

- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `POST /api/v1/orders/{order_id}/cancel`
- `POST /api/v1/orders/{order_id}/reorder`

### 7. Favorites Domain

Flutter home app bar and restaurant cards imply favorites or wishlist behavior.

Needed backend features:

- favorite restaurants
- favorite menu items later

Current backend status:

- no favorites API or model exists yet

Needed tables:

- `favorite_restaurants`
- optionally `favorite_menu_items`

Needed endpoints:

- `GET /api/v1/me/favorites/restaurants`
- `POST /api/v1/me/favorites/restaurants/{restaurant_id}`
- `DELETE /api/v1/me/favorites/restaurants/{restaurant_id}`

### 8. Notifications Domain

Flutter home app bar includes notification behavior.

Needed backend features:

- in-app notification list
- unread count
- mark read

Current backend status:

- no customer notification center exists yet

Needed tables:

- `notifications`
- `notification_receipts` or user-facing read state

Needed endpoints:

- `GET /api/v1/me/notifications`
- `POST /api/v1/me/notifications/{id}/read`
- `POST /api/v1/me/notifications/read-all`

### 9. Customer Preferences Domain

Flutter profile page implies more than name/email/phone.

Likely future preferences:

- payment method preference
- notification preference
- language/currency preference
- marketing preference

Current backend status:

- profile basics exist
- preference modeling does not yet exist

Needed tables:

- `customer_preferences`
- maybe `saved_payment_methods`

### 10. Reviews Domain

Flutter restaurant detail exposes reviews/review entry points conceptually.

Current backend only stores rolled-up rating metrics.

Needed backend features:

- list restaurant reviews
- rating breakdown
- list menu item reviews later
- create review after fulfilled order

Needed tables:

- `restaurant_reviews`
- optionally `menu_item_reviews`

Needed endpoints:

- `GET /api/v1/restaurants/{restaurant_id}/reviews`
- `POST /api/v1/restaurants/{restaurant_id}/reviews`

### 11. Table Booking Domain

Flutter has book-table and select-table flows.

This is a major product decision.

If YummyDoors is expected to support dine-in reservations, backend needs:

- restaurant booking availability
- seating/table inventory
- reservation creation
- reservation confirmation

Current backend status:

- nothing exists for this yet

Needed tables if this is in scope:

- `restaurant_tables`
- `restaurant_table_categories`
- `table_reservations`
- `reservation_status_events`

Needed endpoints:

- `GET /api/v1/restaurants/{restaurant_id}/booking-availability`
- `POST /api/v1/restaurants/{restaurant_id}/reservations`
- `GET /api/v1/me/reservations`

If dine-in is not part of V1, this should be explicitly postponed instead of half-designed.

## Homepage Parity: What Backend Already Has vs What UI Still Ignores

Current `GET /api/v1/home/feed` already returns:

- `location_context`
- `categories`
- `restaurants`
- `promos`
- `recommended_items`
- `popular_foods`

This is good.

Current gap is not only backend.
The current desktop homepage still ignores or underuses several of these:

- `location_context`
- `promos`
- `recommended_items`
- `popular_foods`

It also still uses fake display values in places like:

- category counts
- category average price
- static trending terms
- synthetic restaurant offer badges

So for homepage parity, the backend contract is reasonably shaped already, but the frontend consumption is incomplete.

## Priority Order For Backend Buildout

If we are building the backend properly from the Flutter product shape, the order should be:

1. restaurant detail contract
2. category filtering and search
3. cart domain
4. checkout domain
5. orders domain
6. favorites
7. notifications
8. reviews
9. customer preferences
10. optional table booking

## Recommended Immediate Next Implementation

The best next backend implementation is:

### Phase 1

- add restaurant detail endpoint
- add category-filtered restaurant browse
- add search endpoints

### Phase 2

- create cart tables and cart API
- create checkout preview
- create place-order flow

### Phase 3

- create orders listing/detail/status
- add favorites
- add notifications

## Final Read

Right now YummyDoors backend is strong in:

- identity
- profile
- discovery
- merchant onboarding
- admin ingestion

It is still missing the main commerce engine required by the Flutter product:

- restaurant detail
- cart
- checkout
- orders
- search
- favorites
- notifications
- reviews
- optional booking

That is the real gap exposed by reading the hardcoded Flutter app.
