# YummyDoors Flutter API Parity TODO

This doc tracks the backend work needed to replace the hardcoded and mock data
in `yummydoors_mobile` with real API integrations.

## Goal

Bring `yummydoors_backend` to a point where the Flutter app can consume real
data for:

- homepage
- search and filtering
- restaurant detail
- reviews
- cart and checkout
- orders
- saved addresses
- merchant/customer operational flows

## Current Status

### Ready now

- auth
- home feed
- restaurant list
- restaurant detail
- menu list and menu item detail
- customer profile
- customer addresses
- carts
- orders and checkout

### Still missing or too thin

- wishlist/favorites
- reservations / table booking merchant UI and advanced slot rules
- review create/update moderation flow
- coupon catalog and promo validation rules beyond starter cart contract
- delivery rider/live tracking payloads
- checkout payment gateway integrations

## Implementation Phases

### Phase 1: Discovery and Detail Foundation

- [x] write this TODO doc
- [x] add restaurant search endpoint
- [x] add restaurant list filtering and sorting contract
- [x] enrich restaurant detail response
- [x] add reviews endpoint and detail review summary

### Phase 2: Cart and Checkout Parity

- [x] bind cart to selected customer address
- [x] add cart pricing breakdown
- [x] support notes such as cutlery and cooking request
- [x] add starter coupon / promo application contract

### Phase 3: Orders Parity

- [x] add order timeline states and events
- [x] add address snapshot to orders
- [x] add pricing breakdown snapshot to orders
- [x] support better order tracking payloads for Flutter tracking UI

### Phase 4: Secondary Product Flows

- [ ] wishlist / favorites
- [x] reservations / table booking backend foundation
- [ ] reservations / table booking desktop/admin UI and advanced scheduling rules
- [x] restaurant facilities and extended content sections
- [ ] merchant-side content management for the new fields

## Screen Mapping

### Home Page

Needs:

- categories
- hero promos
- banner promos
- restaurants
- popular foods
- recommended items
- selected location context
- quick address context

Status:

- backend feed contract is ready
- location-aware restaurant filtering still needs a real serving-radius rule

### Restaurant Detail

Needs:

- restaurant summary
- menu sections
- featured items
- popular items
- related restaurants
- opening hours
- open/closed state
- pickup capability
- table booking capability
- contact info
- distance
- about section
- facilities
- reviews summary and list

Status:

- backend contract is now ready for real integration
- merchant editing for every new metadata field still needs follow-through in UI

### Search and Filters

Needs:

- text search across restaurants and menu items
- filters for food type, free delivery, delivery/pickup, open now, featured
- sort options such as recommended, rating, delivery time, highly reordered

Status:

- backend contract is now ready

### Cart / Checkout

Needs:

- selected address binding
- line items
- notes and preferences
- subtotal
- delivery fee
- service fee / tax
- discount
- final total

Status:

- backend contract is now ready
- coupon validation is starter-level and still needs a real promo rule engine

### Orders

Needs:

- richer status lifecycle
- tracking steps
- address snapshot
- payment summary snapshot
- restaurant summary

Status:

- backend contract is now ready
- rider/live map tracking is still missing

## This Turn

This rollout completed:

1. search endpoint
2. filter/sort query contract
3. richer restaurant detail contract
4. reviews contract
5. cart address, pricing, notes, and coupon contract
6. order address snapshot, pricing, and timeline contract

## Next Backend Slice

1. wishlist / favorites
2. real reservation slot rule engine
3. coupon catalog and validation model
4. live rider/tracking payload shape
