# YummyDoors Ecosystem Current State

This is the current system shape after the customer-first and merchant-mode work.

## 1. Product surfaces

## `yummydoors_mobile`

Not wired for merchant mode yet on purpose.

Reason:

- the merchant UX should be designed properly from scratch
- we do not want to force desktop-first UI ideas into mobile

So mobile remains a future design and implementation surface.

## `yummydoors_desktop`

This is currently the shared web product surface for:

- customer mode
- merchant mode

It is not a superadmin site.

It now contains:

- customer auth
- homepage/discovery
- profile/address surface
- merchant mode onboarding surface
- merchant restaurant context switching surface
- links into merchant operations areas

## `yummydoors_admin`

This stays separate.

It is for:

- super admin
- ops/admin review
- ingestion and system control

It is not the customer/merchant app.

## `yummy_backend`

This remains the POS and restaurant-operations backend when a restaurant is POS-connected.

It is not replaced by YummyDoors.

## 2. Identity model

YummyDoors now follows:

- one account
- multiple modes / contexts

The same user can be:

- a customer
- a merchant
- later a multi-restaurant merchant

without creating separate auth identities.

## 3. Backend ownership model

In `yummydoors_backend`, the important entities are now:

- `users`
- `workspaces`
- `workspace_memberships`
- `merchant_applications`
- `merchant_restaurant_requests`
- `restaurant_user_assignments`
- `restaurant_pos_links`

### Meaning

## `users`

Core identity.

## `workspaces`

Context containers inside that identity.

Current workspace types:

- `customer`
- `merchant`

## `workspace_memberships`

Tells which user belongs to which workspace.

## `merchant_applications`

The business onboarding / expansion request object.

## `merchant_restaurant_requests`

The restaurant-level intent inside a merchant application.

Current request types:

- `create_external`
- `claim_existing`
- `pos_link`

## `restaurant_user_assignments`

Actual relationship between a user and a restaurant after approval.

## `restaurant_pos_links`

The structural place where a restaurant in Doors maps to a restaurant in POS.

## 4. Default user flow

When a user signs up or logs in with Google:

1. user account exists
2. `customer` role exists
3. a personal customer workspace is ensured
4. that customer workspace becomes active

So auth always starts in customer mode.

## 5. Merchant flow

Inside desktop, the user can now open merchant mode.

Possible request flows:

## Create external restaurant

Used when the restaurant should start directly in YummyDoors.

Effect:

- merchant application created
- external restaurant request created
- application submitted for review
- on approval, restaurant can be created and attached to merchant owner

## Claim existing restaurant

Used when a restaurant already exists in YummyDoors but the correct merchant owner needs to be attached.

Effect:

- merchant application created
- request references existing YummyDoors restaurant
- ops/admin reviews ownership request
- on approval, merchant gains owner relationship

## POS-linked request

Used when the user should operate a restaurant that is connected to Yummy POS.

Effect:

- merchant application created
- request references an existing YummyDoors restaurant
- request also carries the POS restaurant identity
- review can confirm ownership and later complete POS-connected operations flow

## 6. Merchant context after approval

After merchant approval:

- merchant workspace becomes active/usable
- merchant gets restaurant ownership assignment
- merchant gets `restaurant_owner` role for that restaurant

If the merchant later owns more restaurants:

- those restaurants remain under the same merchant identity
- restaurant context switching happens inside merchant mode

This is why we added:

- `active_restaurant_id` on the user

That gives us the first real base for:

- Restaurant A mode
- Restaurant B mode

inside one merchant workspace.

## 7. Desktop state now

`yummydoors_desktop` now understands:

- `active_workspace`
- `workspaces`
- `active_restaurant_id`

Merchant page now supports:

- homepage-matching merchant UI
- merchant workspace status
- active application visibility
- create external request flow
- claim existing request flow
- POS-linked request flow
- active restaurant switching
- links to category/menu/promo/restaurant management areas

## 8. What is done vs not done

## Done

- customer-first auth model
- merchant workspace model
- merchant onboarding model
- merchant request types for external / claim / POS-linked
- merchant restaurant context switching backend
- desktop merchant onboarding UI
- desktop merchant portal landing surface

## Not done yet

- full merchant operations dashboard per restaurant
- merchant-specific menu editing UX
- merchant-specific category management UX
- merchant-specific promo editing UX
- staff invites / merchant team management
- courier mode
- mobile merchant UX
- cart / checkout / order flow completion
- full POS sync lifecycle

## 9. What this means architecturally

YummyDoors now has one shared identity layer, but the customer experience is still the main product spine.

That means the system should be read in this order:

1. auth and mode selection
2. homepage feed
3. restaurant detail and menu discovery
4. cart and checkout
5. orders and tracking
6. merchant setup and merchant operations
7. POS-linked expansion

## 10. Homepage feed shape now

The homepage feed in `yummydoors_backend` now supports separate promo placements instead of one undifferentiated promo list.

Current response shape includes:

- `location_context`
- `categories`
- `restaurants`
- `promos`
- `hero_promos`
- `banner_promos`
- `recommended_items`
- `popular_foods`

Meaning:

- `hero_promos`
  - used right below the hero/search section
  - mirrors the mobile promo carousel intent

- `banner_promos`
  - used below categories
  - mirrors the lower mobile promo-banner block

- `promos`
  - compatibility field
  - currently falls back to the hero promo list when present

## 11. Restaurant detail shape now

The restaurant detail API already returns enough for a much better customer page than the old backend-demo wording.

Current response includes:

- `restaurant`
- `menu_sections`
- `featured_items`
- `popular_items`
- `related_restaurants`

Desktop now uses that for:

- hero and trust signals
- recommended dishes
- grouped menu sections
- about restaurant block
- photo/gallery block from available assets
- reviews summary block
- related restaurants

## 12. What still remains product-critical

The biggest remaining product gaps are still:

- cart
- checkout
- order creation
- order history and tracking
- fuller restaurant-detail parity beyond current data
- richer merchant operations beyond profile, menu, and promos

So the system is no longer only at auth-plus-mock stage.

But it is also not yet a complete delivery product until the ordering spine is finished.

YummyDoors is now no longer just:

- auth
- customer homepage
- POS linking notes

It now has the first real ecosystem structure:

- customer experience
- merchant onboarding
- merchant operating context
- admin review layer
- future POS-connected execution path

That is the correct product direction.
