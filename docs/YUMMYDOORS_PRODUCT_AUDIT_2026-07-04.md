# YummyDoors Product Audit

Date: 2026-07-04

This document audits what YummyDoors is supposed to be, what has actually been built in `yummydoors_backend` and `yummydoors_desktop`, and where the current product still drifts from the intended system.


## 1. The intended product

From the conversation history and the current Flutter app shape, YummyDoors is supposed to be:

- one shared app for customer and merchant
- customer mode first
- merchant mode under the same identity
- later multi-restaurant merchant context
- desktop as the web version of the mobile product
- superadmin kept separate
- POS-linked restaurants supported, but not the only path
- external restaurants also supported

This means auth and user mapping are only one small part of the system.

The real product is a food ordering ecosystem with:

- homepage discovery
- restaurant browsing
- restaurant detail
- cart and checkout
- orders
- customer profile/address
- merchant onboarding
- merchant restaurant context
- later merchant operations
- later POS-connected lifecycle


## 2. What the Flutter app says the product should look like

Verified from `yummydoors_mobile`:

### Homepage shape

From `lib/features/home/presentation/pages/home_page.dart` the homepage renders:

- location header
- search
- promo carousel
- category strip
- filter chips
- promo banners
- recommended section
- popular food section
- restaurant feed

### Restaurant detail shape

From `lib/features/home/presentation/pages/restaurant_detail_page.dart` the restaurant flow is much richer than a simple menu list. It contains:

- hero header
- action chips like delivery / book table / order later
- food tab
- restaurant detailed tab
- search inside restaurant
- recommended section
- filter chips
- category tabs
- food item detail flow
- about restaurant
- menu section
- photos section
- reviews section
- fixed bottom action bar

### Other customer product areas visible in mobile

- cart
- add delivery address
- orders
- profile
- search page

So the real YummyDoors customer app is broader than just auth + restaurants + a merchant request page.


## 3. What is actually built now

## Backend: done

Verified in `yummydoors_backend`:

- auth exists
- customer workspace auto-creation exists
- merchant workspace/application model exists
- merchant restaurant request flows exist:
  - `create_external`
  - `claim_existing`
  - `pos_link`
- homepage feed exists at `GET /api/v1/home/feed`
- restaurant list exists at `GET /api/v1/restaurants`
- restaurant detail exists at `GET /api/v1/restaurants/{slug}`
- cart APIs exist
- order/checkout APIs exist
- POS match lookup exists by email
- restaurant ownership assignment model exists
- restaurant POS link model exists

Important outcome:

The backend is no longer just auth scaffolding. It already has the base of the product ecosystem.

## Desktop: partial

Verified in `yummydoors_desktop`:

- homepage is connected to `/home/feed`
- restaurants page is connected
- restaurant detail page is connected
- auth is connected
- profile exists
- merchant onboarding/request page exists
- merchant restaurant switching exists
- navbar exposes merchant entry

Important outcome:

Desktop is partially wired, but still exposes too much scaffold behavior and too little product-complete behavior.


## 4. Current flaws

## Flaw 1: restaurant detail is still scaffolded, not product-correct

Current desktop restaurant detail page still contains implementation-style placeholder copy and status-like UI.

Examples from `app/(dashboard)/restaurants/[slug]/page.tsx`:

- fallback description says the backend is connected
- `Quick facts`
- `Ready for ordering flow`
- `Cuisine: Not set`
- `Offer: No current offer`
- `Free delivery: Not available`
- `Menu sections: 1`

This is the exact reason the screen feels wrong.

Problem:

- this is not user-facing YummyDoors language
- this is not aligned with the mobile restaurant detail concept
- it presents backend completeness as if it were customer value

Reality:

The page is technically wired, but not product-ready.

## Flaw 2: homepage is still hybrid, not truly live

The homepage still carries fallback hardcoded arrays for:

- categories
- restaurants
- promos
- recommended items
- location context

That means the homepage is currently:

- dynamic when API data exists
- mock-driven when it does not

Problem:

- this is useful for resilience during development
- but it is not fully dynamic
- it can hide missing backend/data issues
- it makes it hard to know what is really live

## Flaw 3: merchant mode is mostly onboarding, not operations

The current merchant implementation is mostly:

- create external restaurant request
- claim existing restaurant request
- request POS-linked access
- switch active restaurant

This is useful and correct as a foundation.

But it is not yet a full merchant mode.

Missing from real merchant mode:

- restaurant profile management
- menu management
- category management
- offer/promo management
- delivery settings management
- order operations
- restaurant opening hours
- branch/context operations

So the merchant side currently behaves more like:

- business account onboarding

not like:

- a complete merchant operating surface

## Flaw 4: customer/merchant mode system is only partially expressed in UI

The backend identity model is already heading in the correct direction:

- one account
- multiple workspaces/contexts
- later multi-restaurant merchant state

But the desktop UI still expresses this too shallowly.

Current behavior is closer to:

- customer app
- plus merchant entry button

It is not yet a proper mode-aware product where:

- customer mode is obvious
- merchant mode is obvious
- active merchant restaurant context is obvious
- future multi-restaurant switching feels native

## Flaw 5: POS linking exists structurally, but not as a finished business flow

The backend can already inspect Yummy POS user/restaurant matches by email and return candidate restaurant contexts.

That means:

- detection exists
- structural linking direction exists

But full business flow is still incomplete:

- explicit confirmation flow is still limited
- actual operational sync flow is not complete
- imported menu/category ownership lifecycle is not complete
- merchant UI does not yet fully explain POS-connected state in a natural way

So POS linking is real in structure, but not complete as a mature product workflow.

## Flaw 6: desktop still under-represents the customer commerce flow

The backend already has cart and order foundations.

But the visible web product still under-exposes:

- cart flow
- checkout flow
- orders flow
- restaurant-to-cart UX
- item detail to cart UX

This matters because YummyDoors is not only a discovery product. It is an ordering product.

## Flaw 7: some current UI speaks like a system demo

This is the deeper pattern behind multiple issues.

Some areas still communicate things like:

- backend-ready
- live from backend
- connected to API
- ready for ordering flow

Problem:

That is internal progress language.

A customer product should instead communicate:

- food
- delivery
- offers
- reviews
- timings
- restaurant story
- ordering actions


## 5. What is already correct

Despite the flaws above, the direction is not wrong.

These parts are good and should remain:

- one-account multi-mode direction
- customer-first auth
- separate superadmin app
- support for both external and POS-linked restaurants
- merchant request types:
  - create external
  - claim existing
  - pos link
- restaurant assignment ownership model
- active restaurant context concept
- homepage feed as a composed API
- restaurant detail endpoint as a dedicated contract

These are good foundations. The main issue now is product shaping and visible flow completion.


## 6. What the system is right now in plain English

Right now YummyDoors is:

- a real backend foundation for customer discovery, merchant onboarding, restaurant ownership, POS matching, carts, and orders
- a partially wired desktop app
- a desktop app that is ahead of pure mockup stage, but still behind product-complete stage

The biggest mismatch is:

- backend has grown into a real system
- desktop still shows parts of it like a scaffold/demo


## 7. Correct implementation priority from here

This is the clean order to continue without drifting again.

## Priority 1: fix restaurant detail properly

This should be the next major surface to clean up.

Reason:

- it is visibly wrong right now
- it is where the product language drift is most obvious
- mobile already tells us what this screen should roughly contain

Target:

- remove scaffold wording
- use product wording
- shape sections around actual customer restaurant experience
- align with mobile concepts:
  - food tab
  - restaurant detail tab
  - menu groupings
  - reviews entry
  - about restaurant
  - action states

## Priority 2: make homepage truly dynamic

Keep graceful loading states, but remove product-shaping fallback data over time.

Target:

- the page should reveal missing data honestly
- seeded backend data should drive the experience
- frontend should stop masking missing backend records with hardcoded product content

## Priority 3: complete customer commerce on desktop

Use the existing backend foundation and wire:

- cart
- checkout
- orders
- restaurant item ordering flow

This brings the web product closer to the mobile product’s actual purpose.

## Priority 4: evolve merchant from onboarding into operations

Keep the request flow, but add post-approval merchant behavior:

- manage restaurant profile
- manage categories
- manage menu
- manage promos
- manage delivery settings
- later manage orders

## Priority 5: mature POS-linked merchant flow

After the merchant operations base is stronger:

- improve POS-linked identity explanation
- improve claim/link confirmation UX
- add clearer linked-state behavior
- later add controlled import/sync workflow


## 8. Done / Partial / Missing / Wrong-for-product

## Done

- auth foundation
- one-account workspace direction
- merchant application domain
- external restaurant onboarding path
- claim existing restaurant path
- POS-linked request path
- homepage backend feed
- restaurant list backend
- restaurant detail backend
- cart backend foundation
- order backend foundation

## Partial

- homepage desktop
- restaurant detail desktop
- merchant mode desktop
- POS-linked UX
- customer profile/address productization
- customer mode vs merchant mode expression

## Missing

- fully product-correct restaurant detail experience
- fully dynamic homepage without content-like fallbacks
- full cart/checkout/orders web flow
- real merchant operations surface
- refined multi-restaurant merchant UX
- mature POS-connected operational lifecycle

## Wrong for product right now

- implementation-style copy shown to users
- placeholder “status” cards presented as customer-facing restaurant information
- merchant currently feeling more like a setup wizard than a real mode


## 9. Bottom line

The system is not empty.

The backend already contains a meaningful base for the YummyDoors ecosystem.

But the visible product is still drifting in a few important places:

- restaurant detail is the clearest broken product-language surface
- homepage is still partly protected by mock-like fallbacks
- merchant exists as a foundation, not yet as a complete mode
- customer ordering flow is not yet fully expressed in desktop

So the next work should focus less on adding more raw structure, and more on turning the existing structure into a product-correct experience.
