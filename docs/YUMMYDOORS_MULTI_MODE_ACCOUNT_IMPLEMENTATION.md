# YummyDoors Multi-Mode Account Implementation

This backend now follows the account model we aligned on:

- one user identity
- customer mode by default
- merchant mode added later under the same account
- superadmin kept separate in `yummydoors_admin`

## What this means

When a user registers or signs in with Google:

1. a normal `users` record exists
2. the `customer` role exists as before
3. a personal `customer` workspace is created automatically
4. that workspace becomes the user's `active_workspace_id`

So the user starts as a customer, not as a restaurant operator.

## New backend concepts

## `workspaces`

Represents account contexts inside the same identity.

Current supported types:

- `customer`
- `merchant`

Later we can add:

- `courier`
- multi-restaurant merchant child contexts

## `workspace_memberships`

Represents which users belong to which workspaces and with what membership role.

Examples:

- one user owns their personal customer workspace
- the same user also owns a merchant workspace
- later multiple staff can be added to one merchant workspace

## `merchant_applications`

Represents merchant onboarding for a user.

Lifecycle now:

- `draft`
- `submitted`
- `approved`
- `rejected`

## `merchant_restaurant_requests`

Represents the restaurant intent inside a merchant application.

Current supported request types:

- `create_external`
- `claim_existing`
- `pos_link`

This is the first proper bridge between:

- customer identity
- merchant expansion
- restaurant ownership
- later POS-connected restaurant linkage

## API surface added

## Workspace APIs

- `GET /api/v1/workspaces/me`
- `POST /api/v1/workspaces/switch`

These give the frontend the current account contexts and let it switch between them.

## Merchant self-serve APIs

- `GET /api/v1/merchant/applications/me`
- `POST /api/v1/merchant/applications`
- `GET /api/v1/merchant/applications/{application_id}`
- `PATCH /api/v1/merchant/applications/{application_id}`
- `POST /api/v1/merchant/applications/{application_id}/restaurant-requests`
- `POST /api/v1/merchant/applications/{application_id}/submit`

These are what the shared mobile/web app should call when a customer chooses:

- create business account
- add your restaurant

## Admin review APIs

- `GET /api/v1/admin/merchant-applications`
- `POST /api/v1/admin/merchant-applications/{application_id}/approve`
- `POST /api/v1/admin/merchant-applications/{application_id}/reject`

These are for ops or superadmin review.

## What approval does now

When a submitted merchant application is approved:

1. a merchant workspace becomes active
2. restaurant requests are marked approved
3. external restaurants can be created automatically
4. the user gets restaurant ownership assignment
5. the user gets the `restaurant_owner` role scoped to that restaurant

So the same user can now operate as:

- customer
- restaurant owner

under one account.

## What the frontend should do next

In `yummydoors_mobile` and `yummydoors_desktop`:

1. keep login/signup customer-first
2. call `GET /workspaces/me` after auth bootstrap
3. show current mode from `active_workspace`
4. show CTA like `Create business account` if no merchant workspace exists
5. run merchant onboarding using the merchant application endpoints
6. switch mode with `POST /workspaces/switch`

## What is still not done

- staff invites into merchant workspaces
- courier workspaces
- real merchant portal screens
- actual POS import and sync jobs
- restaurant claim verification rules
- order/cart/checkout lifecycle
- merchant approval automation

This implementation gives us the proper foundation for those next steps without splitting auth into separate products.
