# YummyDoors Product Understanding And Frontend Contract

## 1. Corrected product understanding

This is the corrected understanding after checking `yummydoors_mobile` directly.

- `yummydoors_mobile` is the current source of truth for the customer product.
- `yummydoors_desktop` should be the web version of the same customer product.
- `yummydoors_backend` should serve both mobile and web customer apps.
- a separate admin/operator portal should be built later as a different product surface.
- `yummy_backend` remains the POS / restaurant operations backend and should integrate into YummyDoors where needed.

This means YummyDoors is **not** mainly an auth dashboard or POS-linking tool.

YummyDoors is primarily:
- restaurant discovery
- restaurant detail and menu browsing
- cart and checkout
- delivery address management
- order placement
- order history and tracking
- customer profile

POS user mapping is only one small integration/settings layer inside that bigger ecosystem.


## 2. What `yummydoors_mobile` shows about the real system

From the current mobile routes and screens, the customer product surface includes:

- home feed
- search
- restaurant detail
- menu page
- restaurant reviews
- cart page
- cart detail
- add delivery address
- restaurant order summary
- orders page
- order overview
- order tracking
- profile page
- edit profile page
- book table
- select table
- table reservation success

Important note:

- the mobile app is still heavily mock-data driven
- the route structure and screen shape are real product signals
- the backend should be planned against those product flows, not against the current mock implementation


## 3. What the backend should optimize for after auth

After auth, the next backend priority should be the customer product spine:

1. customer profile and addresses
2. home feed and restaurant discovery
3. restaurant detail and menu
4. cart
5. checkout and order creation
6. orders and tracking
7. optional table booking
8. POS-connected restaurant integration where relevant

This is a better priority order than continuing with only POS user linking.


## 4. Current frontend-to-backend understanding

## 4.1 Auth

Already needed:

- sign up
- sign in
- forgot password
- reset password
- get current user
- update current user profile later

Current Doors auth is foundational, but it is not the main product.


## 4.2 Home feed

`yummydoors_mobile` has a `HomeRepository.getHomeFeed()` contract.

The backend should eventually send one home feed payload shaped like:

```json
{
  "categories": [],
  "promos": [],
  "restaurants": [],
  "popular_foods": []
}
```

Recommended response contract:

- `categories`
  - `id`
  - `name`
  - `icon_url`
  - `sort_order`

- `promos`
  - `id`
  - `title`
  - `subtitle`
  - `image_url`
  - `cta_text`
  - `cta_target`
  - `is_active`

- `restaurants`
  - `id`
  - `name`
  - `slug`
  - `cover_image_url`
  - `logo_url`
  - `rating`
  - `review_count`
  - `eta_minutes`
  - `distance_km`
  - `cuisine_labels`
  - `is_open`
  - `has_free_delivery`
  - `offer_text`

- `popular_foods`
  - `id`
  - `restaurant_id`
  - `restaurant_name`
  - `title`
  - `image_url`
  - `price`
  - `price_label`
  - `spicy_label`
  - `status_label`
  - `progress`


## 4.3 Restaurant list and search

The mobile app clearly expects browsing plus search/filter.

Frontend should be able to ask for:

- restaurant list
- search by text
- filters
  - cuisine
  - rating
  - open now
  - free delivery
  - price or delivery bands later
- sorting
  - recommended
  - rating
  - delivery time
  - distance

Recommended backend responses:

### `GET /restaurants`

Query params:

- `q`
- `category_id`
- `cuisine`
- `min_rating`
- `is_open`
- `free_delivery`
- `sort`
- `page`
- `page_size`

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_next": false
}
```


## 4.4 Restaurant detail

From the mobile screens, restaurant detail should not be only a small summary card.

Frontend needs:

- hero section
- restaurant info
- delivery/pickup/book-table capabilities
- tabs or sections for food vs restaurant detail
- recommended items
- category tabs
- reviews summary
- restaurant status

Recommended detail payload:

```json
{
  "id": 52,
  "name": "Yummy",
  "slug": "yummy",
  "cover_image_url": "",
  "logo_url": "",
  "rating": 4.6,
  "review_count": 388,
  "eta_minutes": 20,
  "distance_km": 3.2,
  "address": "",
  "phone": "",
  "description": "",
  "is_open": true,
  "supports_delivery": true,
  "supports_pickup": true,
  "supports_table_booking": false,
  "has_free_delivery": false,
  "offer_text": null,
  "cuisine_labels": [],
  "recommended_items": [],
  "menu_categories": [],
  "review_summary": {
    "average_rating": 4.6,
    "review_count": 388
  }
}
```


## 4.5 Menu data

The mobile menu and food detail flows imply these backend needs:

- category list
- menu items
- item detail
- dietary tags
- spicy/popular tags
- rating
- customizations / add-ons / modifier groups
- stock state

Recommended item list shape:

- `id`
- `restaurant_id`
- `category_id`
- `name`
- `description`
- `image_url`
- `price`
- `price_label`
- `currency`
- `is_available`
- `is_veg`
- `is_spicy`
- `is_popular`
- `rating`
- `rating_count`
- `modifier_groups`

Recommended modifier group shape:

- `id`
- `name`
- `min_select`
- `max_select`
- `is_required`
- `options`

Recommended modifier option shape:

- `id`
- `name`
- `price_delta`
- `is_available`


## 4.6 Cart

The mobile cart pages imply the backend needs a real server-side cart model, not just local UI state.

Frontend needs:

- current cart by restaurant
- add item
- update quantity
- remove item
- remove unavailable item
- special instructions
- coupon code
- totals
- selected delivery address

Recommended cart payload:

```json
{
  "id": "cart_123",
  "restaurant": {
    "id": 52,
    "name": "Yummy",
    "phone": "9862936014"
  },
  "delivery_address": null,
  "items": [],
  "unavailable_items": [],
  "applied_coupon": null,
  "special_requests": [],
  "pricing": {
    "subtotal": 0,
    "discount": 0,
    "delivery_fee": 0,
    "tax": 0,
    "service_fee": 0,
    "total": 0
  }
}
```

Each cart item should include:

- `id`
- `menu_item_id`
- `name`
- `image_url`
- `quantity`
- `unit_price`
- `total_price`
- `modifier_selections`
- `instructions`
- `is_available`


## 4.7 Delivery addresses

The current add-address page shows the frontend needs these fields:

- recipient name
- phone number
- address
- street number
- email

Recommended stored address model:

- `id`
- `label`
- `recipient_name`
- `phone_country_code`
- `phone_number`
- `email`
- `address_line_1`
- `address_line_2`
- `street_number`
- `city`
- `area`
- `state_or_province`
- `latitude`
- `longitude`
- `delivery_notes`
- `is_default`

Recommended address endpoints:

- `GET /me/addresses`
- `POST /me/addresses`
- `PATCH /me/addresses/{id}`
- `DELETE /me/addresses/{id}`
- `POST /me/addresses/{id}/default`


## 4.8 Checkout and order summary

The current flows imply the frontend needs:

- selected cart
- delivery address
- delivery fee
- taxes
- coupon application result
- payment method options
- order notes
- final payable amount

Recommended order preview payload:

```json
{
  "cart_id": "cart_123",
  "restaurant_id": 52,
  "delivery_address_id": 11,
  "items": [],
  "pricing": {
    "subtotal": 0,
    "discount": 0,
    "delivery_fee": 0,
    "tax": 0,
    "service_fee": 0,
    "total": 0
  },
  "payment_methods": [],
  "validation": {
    "can_place_order": true,
    "errors": []
  }
}
```


## 4.9 Orders and tracking

The mobile app clearly expects:

- all orders
- active orders
- to-pay orders
- order history
- to-review orders
- order overview
- order tracking
- cancel order for some states

Recommended order response shape:

- `id`
- `order_number`
- `restaurant`
  - `id`
  - `name`
  - `logo_url`
  - `tags`
- `status`
- `status_text`
- `eta_label`
- `items`
- `pricing`
- `created_at`
- `can_cancel`
- `can_track`
- `can_review`

Recommended tracking payload:

```json
{
  "order_id": "ord_123",
  "status": "preparing",
  "status_text": "Preparing",
  "eta_minutes": 20,
  "timeline": [
    { "key": "placed", "label": "Order placed", "completed": true, "timestamp": "" },
    { "key": "accepted", "label": "Restaurant accepted", "completed": true, "timestamp": "" },
    { "key": "preparing", "label": "Preparing", "completed": true, "timestamp": "" },
    { "key": "picked_up", "label": "Picked up", "completed": false, "timestamp": null },
    { "key": "delivered", "label": "Delivered", "completed": false, "timestamp": null }
  ]
}
```


## 4.10 Profile

The profile and edit-profile screens imply:

- current customer profile
- update profile
- delete account later
- maybe preferences later

Recommended profile payload:

- `id`
- `full_name`
- `email`
- `phone`
- `avatar_url`
- `date_of_birth` later if needed
- `gender` later if needed
- `default_address_id`


## 4.11 Table booking

The route tree includes:

- book table
- select table
- reservation success

This should be treated as optional phase-two or phase-three work unless the product wants it immediately.

Recommended backend needs if enabled:

- restaurant reservation capability
- table types / slots
- reservation create
- reservation history


## 5. How POS should fit into this ecosystem

POS integration should support the customer delivery system, not define it.

POS should mainly matter when:

- a restaurant in Doors is POS-connected
- the restaurant/menu data comes from or is mapped to POS
- order placement must push into POS
- order status needs sync from POS
- staff / restaurant identity needs mapping for restaurant-facing tools later

So POS-related auth linking is valid work, but it is not the main product spine.


## 6. What frontend should receive first

If we are prioritizing by customer value and mobile/web parity, the first useful backend responses should be:

### Phase 1

- auth user profile
- saved addresses
- home feed
- restaurant list
- restaurant detail
- menu categories and items

### Phase 2

- cart
- coupon apply/remove
- checkout preview
- place order

### Phase 3

- orders list
- order detail
- tracking timeline
- cancel order

### Phase 4

- reviews
- favorites
- table booking
- POS-connected restaurant/order sync


## 7. What is implemented vs not aligned yet

Currently in `yummydoors_backend`:

- auth exists
- password reset exists
- Google sign-in exists
- live POS identity lookup now exists as a small integration slice

But the following are still missing as real customer backend modules:

- addresses
- home feed
- restaurant discovery
- restaurant detail
- menu
- cart
- checkout
- orders
- tracking
- reviews

Currently in `yummydoors_desktop`:

- auth pages exist
- some temporary dashboard work exists

That dashboard work should not be treated as product truth.
Desktop should move toward mobile customer-app parity.


## 8. Recommended next backend steps

The next concrete backend implementation order should be:

1. `me` profile expansion and delivery addresses
2. restaurant feed and restaurant detail
3. menu/category/item contracts
4. cart
5. checkout preview and order creation
6. order history and tracking

That sequence aligns the backend with the real YummyDoors product as shown by `yummydoors_mobile`.
