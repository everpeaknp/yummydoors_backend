# YummyDoors System Blueprint

## Purpose

This document defines how YummyDoors should be structured from the beginning, based on:

- the current high-level tech summary
- the shared planning conversation
- the current Flutter mobile product surface

This is not code yet. It is the blueprint we should build the backend from.

## 1. Current State

## What we have

### Backend repo

Today this backend repo only contains:

- [YUMMYDOORS_TECH_SUMMARY.md](/home/ramon/projects/everacy/yummydoors_backend/YUMMYDOORS_TECH_SUMMARY.md)

So backend implementation status is effectively:

- no app structure
- no FastAPI app
- no database models
- no migrations
- no API contracts
- no background jobs
- no websocket layer
- no POS integration layer
- no admin or restaurant dashboard backend

### Mobile repo

The mobile repo gives us a strong product skeleton:

- home/discovery
- restaurants
- menu
- item detail
- cart
- address
- checkout and payment selection
- orders
- order tracking
- reviews
- profile
- book table
- table selection

But it is still mostly mocked and not yet API-driven.

## What we need

We need to build YummyDoors as a real product platform, not just a customer app backend.

That means the backend must support:

- customer-facing app workflows
- restaurant-facing workflows
- admin and operations workflows
- delivery workflows
- POS integration workflows
- payment workflows
- notification workflows

## 2. Product Ecosystem

YummyDoors is not a single-app system. It is an ecosystem with multiple actors.

## Core actors

### Customer

Uses the Flutter app to:

- browse restaurants
- search food
- add items to cart
- choose delivery/pickup/dine-in context
- place orders
- pay online or COD
- track orders
- leave reviews
- manage profile and saved addresses
- reserve tables

### External restaurant

Uses YummyDoors dashboard directly.

YummyDoors backend is the source of truth for:

- restaurant profile
- menu
- order acceptance/rejection
- prep status
- availability
- promotions
- reservations

### Yummy Partner restaurant

Uses Yummy POS.

POS is the restaurant-side source of truth for:

- operational order handling
- kitchen/prep flow
- billing/inventory rules

YummyDoors still owns:

- customer-facing app state
- customer order tracking view
- delivery state
- promotions and discovery
- customer notifications

### Delivery operations

May eventually include:

- rider app
- dispatcher/ops dashboard
- internal assignment tools

Even before a rider app exists, backend delivery entities are still required.

### Admin / ops team

Needs:

- restaurant onboarding
- compliance/approval
- offer management
- issue resolution
- delivery oversight
- payment/reconciliation visibility

### External systems

- Yummy POS API
- payment gateways
- Firebase
- map/geocoding/routing provider
- object storage/media layer

## 3. Core Architecture

## Recommended architecture

- `FastAPI` modular monolith
- `PostgreSQL` as system of record
- `Redis` for cache, pub/sub, ephemeral state, rate limiting, websocket fanout support
- `Celery` for async jobs
- `WebSockets` for order and delivery live updates

## Why modular monolith first

This product has multiple business areas, but they are tightly coupled at launch:

- customers
- restaurants
- menus
- carts
- orders
- payments
- delivery
- reviews
- reservations
- notifications
- POS sync

Splitting into microservices now would create overhead before the domain is stable.

The right structure is one codebase with strict internal modules.

## 4. High-Level Domain Boundaries

These are the modules the backend should be built around.

### Identity and access

- customer auth
- customer profile
- restaurant user auth
- admin auth
- role and permission handling
- device tokens

### Customer account

- profile
- saved addresses
- preferences
- favorites

### Restaurant catalog

- restaurant profile
- branches/locations
- cuisines and categories
- service modes
- operating hours
- delivery areas
- restaurant media

### Menu and catalog

- menu categories
- menu items
- variants
- add-ons
- availability
- pricing

### Discovery

- home feed
- featured restaurants
- featured items
- search
- cuisine/category browse
- promo banners

### Cart and checkout

- cart
- cart items
- cart item customizations
- coupon application
- fee calculation
- checkout validation

### Orders

- order creation
- order item snapshotting
- status lifecycle
- customer-facing status timeline
- restaurant-facing status logic
- POS-linked order references

### Payments

- payment method abstraction
- payment intents/transactions
- gateway callbacks
- COD flow
- refund handling

### Delivery

- delivery quote
- delivery task/job
- assignment
- live tracking
- delivery status lifecycle

### Reservations

- table inventory
- table categories
- reservation booking
- reservation status
- reservation policies

### Reviews and ratings

- restaurant reviews
- dish reviews if desired later
- review photos
- verified-order linkage

### Notifications

- push notifications
- email/SMS hooks if later
- in-app notification records
- event-triggered delivery

### Integrations

- POS mapping
- POS order push
- POS status pull/push
- webhook handling
- sync audit

## 5. The Critical Business Distinction

This is the most important backend modeling rule.

## Restaurant ownership type

Every restaurant should have a clear ownership/integration mode:

- `external`
- `yummy_partner`

### External restaurant

YummyDoors owns:

- menu
- order lifecycle
- availability
- dashboard workflow
- reservation workflow

### Yummy Partner restaurant

POS owns:

- kitchen/prep operational state
- restaurant-side order processing

YummyDoors owns:

- customer order shell
- delivery shell
- customer notifications
- customer-visible tracking
- discovery, promos, media

This should not be hidden in random booleans. It should be explicit in the schema and business logic.

## 6. Database Design Principles

These principles should guide schema design.

### 1. Separate stable entities from snapshots

Orders must store snapshots of:

- restaurant name
- branch name
- item name
- variant name
- item price
- add-on selections
- tax/fee numbers

Never rely only on live menu tables when displaying historical orders.

### 2. Do not overpack restaurant data into one table

Restaurant data should be normalized into:

- restaurant core record
- branches
- service modes
- operating hours
- media
- delivery zones
- menu relations

### 3. Treat service mode as a real domain concept

Delivery, pickup, and reservation are not cosmetic tabs.

They affect:

- pricing
- availability
- minimum order
- ETA
- order type
- table booking logic

### 4. Track state transitions explicitly

For orders, payments, delivery jobs, and reservations, store lifecycle history instead of only the latest status.

### 5. Keep POS mapping explicit

Every POS-linked entity should have clean external reference fields and sync audit trails.

## 7. Recommended Core Tables

This is the first serious cut of the backend schema.

## Identity and users

### `users`

Purpose:

- customer account

Fields:

- `id`
- `firebase_uid`
- `phone`
- `email`
- `full_name`
- `avatar_url`
- `is_active`
- `created_at`
- `updated_at`

### `user_devices`

Purpose:

- push targets and device management

Fields:

- `id`
- `user_id`
- `platform`
- `device_token`
- `device_id`
- `last_seen_at`
- `is_active`

### `roles`

- customer
- restaurant_admin
- restaurant_staff
- ops_admin
- super_admin

### `user_role_assignments`

- `id`
- `user_id`
- `role_id`
- `restaurant_id` nullable
- `branch_id` nullable

## Customer profile

### `user_addresses`

Fields:

- `id`
- `user_id`
- `label`
- `recipient_name`
- `phone`
- `email`
- `address_line_1`
- `address_line_2`
- `street_number`
- `landmark`
- `city`
- `state_region`
- `country_code`
- `postal_code`
- `latitude`
- `longitude`
- `is_default`

### `user_favorites`

Fields:

- `id`
- `user_id`
- `restaurant_id`
- `created_at`

## Restaurants

### `restaurants`

Purpose:

- business identity

Fields:

- `id`
- `name`
- `slug`
- `description`
- `ownership_type` (`external`, `yummy_partner`)
- `status` (`draft`, `pending_approval`, `active`, `inactive`, `suspended`)
- `primary_cuisine_id` nullable
- `avg_rating`
- `review_count`
- `price_range`
- `supports_delivery`
- `supports_pickup`
- `supports_dine_in`
- `supports_table_booking`
- `created_at`
- `updated_at`

### `restaurant_branches`

Purpose:

- physical locations

Fields:

- `id`
- `restaurant_id`
- `name`
- `phone`
- `email`
- `address_line_1`
- `address_line_2`
- `city`
- `state_region`
- `country_code`
- `latitude`
- `longitude`
- `timezone`
- `is_active`

### `restaurant_media`

Fields:

- `id`
- `restaurant_id`
- `branch_id` nullable
- `media_type` (`logo`, `cover`, `gallery`)
- `file_url`
- `sort_order`

### `cuisines`

- `id`
- `name`
- `slug`

### `restaurant_cuisines`

- `restaurant_id`
- `cuisine_id`

### `restaurant_hours`

Fields:

- `id`
- `branch_id`
- `day_of_week`
- `opens_at`
- `closes_at`
- `is_closed`

### `restaurant_service_modes`

Purpose:

- mode-specific configuration

Fields:

- `id`
- `branch_id`
- `service_mode` (`delivery`, `pickup`, `dine_in`, `reservation`)
- `is_enabled`
- `min_order_amount`
- `base_prep_minutes`
- `base_eta_minutes` nullable
- `accepts_scheduled_orders`

### `delivery_zones`

Fields:

- `id`
- `branch_id`
- `name`
- `polygon_geojson`
- `min_eta_minutes`
- `max_eta_minutes`
- `base_fee`
- `per_km_fee`
- `minimum_order_amount`
- `is_active`

## Menu

### `menu_categories`

- `id`
- `branch_id`
- `name`
- `description`
- `sort_order`
- `is_active`

### `menu_items`

- `id`
- `branch_id`
- `menu_category_id`
- `name`
- `description`
- `image_url`
- `item_type` (`veg`, `non_veg`, `vegan`, etc.)
- `base_price`
- `is_active`
- `is_recommended`
- `is_popular`
- `spicy_level` nullable

### `menu_item_variants`

- `id`
- `menu_item_id`
- `name`
- `price_delta`
- `is_default`
- `is_active`

### `modifier_groups`

- `id`
- `menu_item_id`
- `name`
- `selection_type` (`single`, `multiple`)
- `min_select`
- `max_select`
- `is_required`

### `modifier_options`

- `id`
- `modifier_group_id`
- `name`
- `price_delta`
- `is_active`

### `item_availability_overrides`

- `id`
- `menu_item_id`
- `branch_id`
- `starts_at`
- `ends_at`
- `is_available`

## Discovery and promos

### `home_banners`

- `id`
- `title`
- `subtitle`
- `image_url`
- `target_type`
- `target_id`
- `sort_order`
- `is_active`

### `featured_restaurants`

- `id`
- `restaurant_id`
- `branch_id` nullable
- `sort_order`
- `starts_at`
- `ends_at`

### `promotions`

- `id`
- `restaurant_id` nullable
- `branch_id` nullable
- `title`
- `description`
- `promo_type`
- `discount_type`
- `discount_value`
- `min_order_amount`
- `usage_limit`
- `starts_at`
- `ends_at`
- `is_active`

### `coupon_codes`

- `id`
- `promotion_id`
- `code`
- `max_uses`
- `per_user_limit`
- `is_active`

## Cart

### `carts`

Important rule:

- one active cart per user per restaurant branch and service mode

Fields:

- `id`
- `user_id`
- `restaurant_id`
- `branch_id`
- `service_mode`
- `delivery_address_id` nullable
- `scheduled_for` nullable
- `coupon_code_id` nullable
- `special_instructions` nullable
- `status` (`active`, `converted`, `abandoned`)
- `expires_at`
- `created_at`
- `updated_at`

### `cart_items`

- `id`
- `cart_id`
- `menu_item_id`
- `menu_item_variant_id` nullable
- `quantity`
- `unit_price_snapshot`
- `name_snapshot`

### `cart_item_modifiers`

- `id`
- `cart_item_id`
- `modifier_option_id`
- `name_snapshot`
- `price_snapshot`

## Orders

### `orders`

This is the backbone table.

Fields:

- `id`
- `public_order_number`
- `user_id`
- `restaurant_id`
- `branch_id`
- `service_mode`
- `ownership_type_snapshot`
- `source_system` (`yummydoors`, `pos`)
- `status`
- `payment_status`
- `fulfillment_status`
- `delivery_address_snapshot_json` nullable
- `scheduled_for` nullable
- `subtotal_amount`
- `discount_amount`
- `delivery_fee_amount`
- `service_fee_amount`
- `tax_amount`
- `total_amount`
- `currency_code`
- `customer_note` nullable
- `placed_at`
- `confirmed_at` nullable
- `completed_at` nullable
- `cancelled_at` nullable

### `order_items`

- `id`
- `order_id`
- `menu_item_id` nullable
- `menu_item_variant_id` nullable
- `item_name_snapshot`
- `variant_name_snapshot` nullable
- `quantity`
- `unit_price_snapshot`
- `line_total_amount`
- `item_type_snapshot`

### `order_item_modifiers`

- `id`
- `order_item_id`
- `modifier_option_id` nullable
- `name_snapshot`
- `price_snapshot`

### `order_status_history`

- `id`
- `order_id`
- `status`
- `source` (`system`, `restaurant_dashboard`, `pos_webhook`, `ops`, `delivery`)
- `note` nullable
- `created_at`

### `order_cancellations`

- `id`
- `order_id`
- `cancelled_by_actor`
- `reason_code`
- `reason_text`
- `created_at`

## Payments

### `payment_methods`

- `id`
- `code`
- `name`
- `method_type` (`card`, `wallet`, `cod`)
- `provider`
- `is_active`

### `payments`

- `id`
- `order_id`
- `payment_method_id`
- `provider_payment_ref`
- `amount`
- `currency_code`
- `status`
- `initiated_at`
- `confirmed_at` nullable
- `failed_at` nullable

### `payment_webhook_events`

- `id`
- `provider`
- `event_id`
- `event_type`
- `payload_json`
- `processed_at` nullable
- `status`

### `refunds`

- `id`
- `payment_id`
- `amount`
- `reason`
- `status`
- `created_at`

## Delivery

### `delivery_jobs`

- `id`
- `order_id`
- `branch_id`
- `pickup_latitude`
- `pickup_longitude`
- `drop_latitude`
- `drop_longitude`
- `quoted_fee`
- `quoted_distance_meters`
- `quoted_eta_minutes`
- `status`
- `assigned_at` nullable
- `picked_up_at` nullable
- `delivered_at` nullable

### `delivery_agents`

Only needed if first-party or managed riders exist.

- `id`
- `full_name`
- `phone`
- `vehicle_type`
- `status`
- `is_active`

### `delivery_assignments`

- `id`
- `delivery_job_id`
- `delivery_agent_id`
- `assigned_by_user_id` nullable
- `assigned_at`
- `unassigned_at` nullable

### `delivery_tracking_events`

- `id`
- `delivery_job_id`
- `status`
- `latitude` nullable
- `longitude` nullable
- `note` nullable
- `created_at`

## Reservations

### `restaurant_tables`

- `id`
- `branch_id`
- `table_number`
- `category` (`indoor`, `outdoor`, `terrace`, `private`)
- `seat_count`
- `is_active`

### `table_reservations`

- `id`
- `reservation_code`
- `user_id`
- `restaurant_id`
- `branch_id`
- `restaurant_table_id` nullable
- `guest_count`
- `reservation_date`
- `reservation_time`
- `occasion` nullable
- `contact_name`
- `contact_phone`
- `status` (`pending`, `confirmed`, `cancelled`, `completed`, `no_show`)
- `source`
- `created_at`

### `reservation_status_history`

- `id`
- `table_reservation_id`
- `status`
- `note` nullable
- `created_at`

## Reviews

### `restaurant_reviews`

- `id`
- `restaurant_id`
- `branch_id`
- `user_id`
- `order_id` nullable but recommended
- `rating`
- `title` nullable
- `body`
- `status` (`published`, `hidden`, `flagged`)
- `created_at`

### `review_media`

- `id`
- `restaurant_review_id`
- `file_url`
- `sort_order`

## Notifications

### `notification_templates`

- `id`
- `code`
- `channel`
- `title_template`
- `body_template`

### `notifications`

- `id`
- `user_id`
- `channel`
- `template_code` nullable
- `title`
- `body`
- `status`
- `related_entity_type` nullable
- `related_entity_id` nullable
- `sent_at` nullable

## POS integration

### `pos_restaurant_mappings`

- `id`
- `restaurant_id`
- `branch_id`
- `pos_system`
- `pos_restaurant_ref`
- `pos_branch_ref`
- `sync_status`

### `pos_menu_mappings`

- `id`
- `menu_item_id`
- `pos_item_ref`
- `branch_id`

### `pos_order_links`

- `id`
- `order_id`
- `pos_order_ref`
- `pos_ticket_ref` nullable
- `sync_status`
- `last_synced_at` nullable

### `integration_event_logs`

- `id`
- `integration_name`
- `direction` (`outbound`, `inbound`)
- `entity_type`
- `entity_id`
- `status`
- `request_payload_json`
- `response_payload_json`
- `error_message` nullable
- `created_at`

## 8. API Surface We Need

The backend should eventually expose at least these API groups.

### Customer APIs

- auth/profile
- home feed
- restaurants list/detail
- menu list/detail
- search
- cart CRUD
- address CRUD
- checkout/create order
- payments/initiate
- order history/detail
- order tracking
- reviews
- favorites
- reservations

### Restaurant dashboard APIs

- restaurant profile/settings
- menu management
- promo management
- availability toggles
- reservation handling
- external restaurant order handling

### Ops/admin APIs

- restaurant approval
- issue moderation
- review moderation
- promo management
- delivery oversight
- integration monitoring

### Integration/webhook APIs

- payment callback endpoints
- POS inbound webhook endpoints
- internal integration endpoints

## 9. Realtime Events We Need

WebSockets should primarily support:

- order status updates
- delivery status updates
- live ETA/tracking updates
- restaurant-facing new-order alerts

Do not start with generic websocket chaos. Start with event types and strict payload contracts.

## 10. What The Current Mobile App Implies For Contracts

The mobile app suggests the first backend response shapes we will need.

### Home feed

Needs:

- categories
- promos/banners
- restaurant cards
- popular items

### Restaurant list/detail

Needs:

- rating
- review count
- ETA
- cuisine
- cover image
- logo
- free delivery flag
- offer text
- open/closed state
- supported service modes

### Cart/order

Needs:

- item snapshots
- quantity
- modifiers
- out-of-stock handling
- coupon support
- fee breakdown
- selected address
- payment method selection

### Tracking

Needs:

- order timeline
- delivery status
- ETA window
- rider details if assigned

### Reservation

Needs:

- table categories
- seat count
- availability
- selected slot
- reservation ID

## 11. What We Have vs What We Need

## What we have now

- a high-level stack decision
- a customer mobile prototype
- a visible route map of major user journeys
- enough evidence to derive modules and schema

## What we do not have yet

- backend code
- data contracts
- DB schema
- migrations
- auth implementation
- POS integration contract
- payment integration contract
- delivery orchestration logic
- restaurant dashboard backend
- admin backend
- notification system
- websocket contracts

## 12. Recommended Build Order From Zero

This is the order I would build it in.

### Phase 0: foundation

- repo scaffold
- FastAPI app structure
- config/settings
- SQLAlchemy models
- Alembic
- base auth plumbing
- Redis/Celery wiring

### Phase 1: customer ordering MVP

- users
- addresses
- restaurants
- branches
- menus
- home feed
- cart
- checkout
- order creation
- payment abstraction
- order history/detail

### Phase 2: operational backbone

- order status history
- websocket updates
- notifications
- delivery jobs
- basic delivery tracking
- payment webhooks

### Phase 3: restaurant-side operations

- external restaurant dashboard APIs
- availability toggles
- order accept/reject/prepare flow
- menu management
- promotions

### Phase 4: POS-connected partner mode

- restaurant/POS mappings
- POS order push
- POS status sync
- sync logs and retry jobs

### Phase 5: extended product features

- reservations
- table inventory
- reviews with media
- favorites
- scheduled orders
- advanced discovery/search/ranking

## 13. Practical Engineering Recommendation

Do not build YummyDoors backend as:

- a single flat `orders.py` plus a few tables

Do build it as:

- a modular monolith with explicit domain packages and database ownership boundaries

The first implementation should already respect:

- dual restaurant ownership
- service-mode-aware ordering
- order snapshotting
- payment abstraction
- delivery lifecycle
- POS mapping

If we get those six things right early, the backend will scale with the product instead of being rewritten once dashboard, delivery, and partner integrations get real.
