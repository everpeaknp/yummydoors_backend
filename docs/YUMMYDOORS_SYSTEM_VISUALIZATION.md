# YummyDoors System Visualization

## Purpose

This document visualizes how YummyDoors should work in two cases:

- restaurant is managed fully inside YummyDoors
- restaurant already exists in Yummy POS and is connected into YummyDoors

It also shows how user identity and role assignment should work across both systems.

## 1. The Main Idea

YummyDoors is not only a customer app backend.

It is a separate platform that can serve:

- pure YummyDoors restaurants
- Yummy POS partner restaurants

That means we need to visualize two different restaurant integration modes.

## 2. Two Restaurant Types

## A. External restaurant

This restaurant does not use Yummy POS.

YummyDoors is the source of truth for:

- restaurant profile
- menu
- pricing
- availability
- customer orders
- restaurant-side order handling
- delivery handling
- reservations

## B. POS partner restaurant

This restaurant already exists in Yummy POS.

YummyDoors is the source of truth for:

- customer-facing app presence
- discovery/feed presence
- delivery orchestration
- customer tracking view
- customer notifications
- YummyDoors dashboard permissions

Yummy POS is the source of truth for:

- restaurant-side kitchen flow
- internal prep state
- billing/inventory behavior
- POS-side operational order lifecycle

## 3. System Overview

```text
                    +----------------------+
                    |   Customer Mobile    |
                    |   YummyDoors App     |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  YummyDoors Backend  |
                    |  FastAPI + Postgres  |
                    +----+------------+----+
                         |            |
            +------------+            +----------------+
            |                                            |
            v                                            v
 +------------------------+                 +------------------------+
 | External Restaurant    |                 | POS Partner Restaurant |
 | Dashboard via Doors    |                 | Yummy POS Connected    |
 +-----------+------------+                 +-----------+------------+
             |                                            |
             v                                            v
 +------------------------+                 +------------------------+
 | Orders handled in      |                 | Orders pushed to POS   |
 | YummyDoors directly    |                 | and synced back        |
 +------------------------+                 +------------------------+
```

## 4. Flow Without POS Restaurant

This is the simpler case.

## External restaurant order flow

```text
Customer
  |
  v
YummyDoors Mobile App
  |
  v
YummyDoors Backend
  |
  +--> validates restaurant/menu/cart/pricing
  +--> creates order in YummyDoors DB
  +--> notifies restaurant dashboard
  +--> restaurant accepts/rejects/prepares in YummyDoors
  +--> delivery job created in YummyDoors
  +--> customer sees tracking from YummyDoors
  |
  v
Order completed in YummyDoors
```

## What owns what here

```text
Restaurant data        -> YummyDoors
Menu data              -> YummyDoors
Order lifecycle        -> YummyDoors
Delivery lifecycle     -> YummyDoors
Reservation lifecycle  -> YummyDoors
Customer tracking      -> YummyDoors
```

## 5. Flow With POS Restaurant

This is the partner case.

## POS partner order flow

```text
Customer
  |
  v
YummyDoors Mobile App
  |
  v
YummyDoors Backend
  |
  +--> validates customer/cart/delivery context
  +--> creates local YummyDoors order shell
  +--> maps restaurant and items to POS references
  +--> sends order to Yummy POS API
  |
  v
Yummy POS
  |
  +--> creates POS order/KOT
  +--> kitchen/prep happens in POS
  +--> POS emits status updates
  |
  v
YummyDoors Backend
  |
  +--> updates customer-facing order timeline
  +--> manages delivery state
  +--> sends notifications to customer
  |
  v
Customer sees live status in YummyDoors
```

## What owns what here

```text
Restaurant catalog presence   -> YummyDoors
Discovery/promos/media        -> YummyDoors
Customer order shell          -> YummyDoors
Customer tracking view        -> YummyDoors
Delivery lifecycle            -> YummyDoors
Kitchen/prep operational flow -> Yummy POS
POS billing/inventory rules   -> Yummy POS
```

## 6. The Most Important Distinction

The same restaurant can appear in YummyDoors, but that does not mean YummyDoors fully owns its internals.

That is why each restaurant needs an explicit integration mode.

Example:

```text
restaurants.integration_mode

- external
- pos_partner
```

This single field changes how orders are routed.

## 7. User Identity Visualization

This is the part you asked about most directly.

A person can exist in both systems, but should not be forced to have the same role in both.

## One person, different roles

```text
Person: Sagar

In Yummy POS:
- user_id = 17
- role = waiter

In YummyDoors:
- user_id = 93
- role = restaurant_admin

Link:
- external_user_links
  - system_name = yummy_pos
  - external_user_id = 17
  - local_user_id = 93
```

That is valid.

The same human can have:

- low operational role in POS
- high dashboard/admin role in YummyDoors

because they are different authorization systems.

## 8. User and Role Relationship Diagram

```text
             +------------------+
             |  YummyDoors User |
             |   users.id=93    |
             +--------+---------+
                      |
                      v
             +----------------------+
             | external_user_links  |
             | system = yummy_pos   |
             | external_user_id=17  |
             +--------+-------------+
                      |
                      v
             +------------------+
             |   POS User       |
             |   users.id=17    |
             |   role=waiter    |
             +------------------+


             +------------------+
             |  YummyDoors User |
             |   users.id=93    |
             +--------+---------+
                      |
                      v
             +----------------------+
             | user_roles           |
             | role=restaurant_admin|
             | restaurant_id=21     |
             +----------------------+
```

So:

- identity can be linked
- roles should be assigned independently

## 9. Restaurant Relationship Diagram

```text
             +----------------------+
             | YummyDoors Restaurant|
             | restaurants.id=21    |
             | mode=pos_partner     |
             +----------+-----------+
                        |
                        v
             +----------------------+
             | restaurant_pos_links |
             | pos_restaurant_id=8  |
             | pos_branch_id=3      |
             +----------+-----------+
                        |
                        v
             +----------------------+
             | POS Restaurant       |
             | restaurant_info.id=8 |
             +----------------------+
```

This is how POS restaurants become part of Doors.

Not by sharing one table blindly.

They become visible in Doors through mapping.

## 10. How A POS Restaurant Enters YummyDoors

```text
1. Restaurant already exists in Yummy POS
2. Ops/admin enables it for YummyDoors
3. YummyDoors creates local restaurant record
4. YummyDoors stores POS restaurant mapping
5. Menu/item mappings are created
6. Selected POS users can be linked to YummyDoors users
7. YummyDoors roles are assigned for dashboard access
8. Restaurant becomes live in YummyDoors app
```

## 11. How Role Assignment Works In Practice

Example:

```text
Restaurant: Burger House

POS side:
- Ram is waiter
- Nina is manager

YummyDoors side:
- Ram can be restaurant_admin
- Nina can be restaurant_staff

This is okay because:
- POS role controls POS actions
- Doors role controls Doors actions
```

## 12. What We Should Not Do

Do not do this:

```text
If POS role = waiter
then Doors role must also be waiter
```

That would be wrong.

Why:

- POS roles are designed for POS operations
- Doors roles are designed for delivery/discovery/dashboard operations

They are related, but not identical.

## 13. Recommended Data Model For This Visualization

These are the key tables behind the picture.

### Identity

- `users`
- `roles`
- `permissions`
- `user_roles`

### Cross-system user link

- `external_user_links`

Suggested fields:

- `id`
- `user_id`
- `system_name`
- `external_user_id`
- `external_role_snapshot`
- `external_restaurant_id`
- `metadata_json`

### Restaurant core

- `restaurants`
- `restaurant_branches`

### Cross-system restaurant link

- `restaurant_pos_links`

Suggested fields:

- `id`
- `restaurant_id`
- `branch_id`
- `pos_restaurant_id`
- `pos_branch_id`
- `sync_mode`
- `is_active`

### Scoped restaurant access

- `restaurant_user_assignments`

Suggested fields:

- `id`
- `user_id`
- `restaurant_id`
- `branch_id` nullable
- `assignment_type`

## 14. Final Mental Model

Use this mental model:

```text
YummyDoors owns:
- its own users
- its own roles
- its own restaurant records
- its own customer orders
- its own delivery logic

Yummy POS may be linked to:
- some users
- some restaurants
- some menu items
- some orders

But linkage is explicit, not merged blindly.
```

## 15. Short Version

Without POS:

- YummyDoors runs the whole restaurant workflow

With POS:

- YummyDoors runs the customer and delivery side
- POS runs the restaurant operational side

For users:

- one human can exist in both systems
- one human can have different roles in each system
- YummyDoors role assignment should be independent from POS role naming
