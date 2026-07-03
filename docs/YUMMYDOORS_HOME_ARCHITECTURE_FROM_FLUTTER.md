# YummyDoors Homepage Architecture From Flutter

This document designs the homepage backend from the actual `yummydoors_mobile` Flutter app surface.

The goal is to start from **frontend fields first**, then derive:

- root domain entities
- backend modules
- database tables
- API contracts
- implementation order

This avoids building homepage APIs from guesswork.


## 1. What the Flutter homepage actually renders

From `lib/features/home/presentation/pages/home_page.dart`, the homepage is composed of:

1. location header
2. search entry
3. promo carousel
4. cuisine/category strip
5. filter chips
6. promo banner carousel
7. recommended section
8. popular food section
9. restaurant feed cards

So the homepage is not a single data object. It is a composition of several data domains.


## 2. Field inventory from Flutter widgets

## 2.1 Location header

From `home_app_bar.dart` and `location_picker_sheet.dart`

Rendered fields:

- `location_title`
  - example: `Ratnachowk`
- `location_subtitle`
  - example: `Pokhara,street No 14`
- current selected saved address label
- list of saved addresses
- whether an address is selected
- add new address action
- current-location action

This implies the backend needs:

- current customer context
- selected delivery address
- saved delivery addresses
- maybe geolocation later


## 2.2 Search entry

Rendered fields:

- `hint_text`
- open search screen action

This implies the backend will eventually need:

- restaurant search
- menu item search
- maybe cuisine/category search

Search does not need to block homepage MVP, but the data model should not make it hard later.


## 2.3 Promo carousel

From `promo_carousel.dart` and `PromoEntity`

Current fields:

- `id`
- `title`
- `subtitle`
- `banner_asset_path`

Backend version should become:

- `id`
- `title`
- `subtitle`
- `image_url`
- `placement`
- `sort_order`
- `is_active`
- `start_at`
- `end_at`
- `target_type`
- `target_id`
- `cta_text`

Important:

- promo content is a merchandising domain
- it should not be hardcoded into restaurants or categories


## 2.4 Category strip

From `category_strip.dart` and `CategoryEntity`

Current fields:

- `id`
- `title`
- `asset_path`
- `selected_id`

Backend version should become:

- `id`
- `slug`
- `name`
- `icon_url`
- `sort_order`
- `is_active`
- `is_featured`

Important dependency:

- categories alone are not useful
- they need to classify restaurants and/or menu items

So category data depends on catalog data behind it.


## 2.5 Filters

From `filter_bottom_sheet.dart`

Current visible filter groups:

- sort
  - relevance
  - distance low to high
  - rating high to low
  - cost high to low
- rating
  - rated 3.5+
  - rated 4+
- offers
- dish price
- trust markers
- time

This implies the backend should support filter metadata and filtered feed queries.

At minimum:

- `sort`
- `min_rating`
- `free_delivery`
- `is_open`
- `max_eta_minutes`
- `price_band`
- `offer_available`


## 2.6 Restaurant cards

From `restaurant_card.dart` and `RestaurantEntity`

Current rendered fields:

- `id`
- `name`
- `image_asset_path`
- `logo_asset_path`
- `is_open`
- `rating`
- `review_count`
- `eta_minutes`
- `distance`
- `cuisine`
- `has_free_delivery`
- `offer_text`

Behavior fields:

- favorite toggle
- tap to restaurant detail

Backend version should become:

- `id`
- `slug`
- `name`
- `cover_image_url`
- `logo_url`
- `is_open`
- `rating`
- `review_count`
- `eta_minutes`
- `distance_km`
- `distance_label`
- `cuisine_labels`
- `has_free_delivery`
- `offer_text`
- `supports_delivery`
- `is_favorited`


## 2.7 Recommended section

From `recommended_food_card.dart`

Important observation:

- the current Flutter screen reuses `RestaurantEntity` for recommended food-style cards
- that is a UI shortcut, not a correct domain model

Rendered fields in that card:

- background food image
- food name
- likes text
- price
- add button
- bookmark state

So the correct backend entity should not be `RestaurantEntity`.
It should be something like:

- `featured_menu_item`
  - `id`
  - `restaurant_id`
  - `restaurant_name`
  - `name`
  - `image_url`
  - `price`
  - `price_label`
  - `likes_count` or popularity metric
  - `is_bookmarked`
  - `is_available`

This is one of the clearest signs that the current mobile app is mock-first.


## 2.8 Popular food section

From `popular_food_card.dart` and `PopularFoodEntity`

Current fields:

- `id`
- `title`
- `price_label`
- `image_asset_path`
- `spicy_label`
- `status_label`
- `progress`

Rendered food traits:

- food image
- add button
- non-veg icon
- spicy label
- title
- reorder/popularity progress
- popularity label
- price

Backend version should become:

- `id`
- `restaurant_id`
- `restaurant_name`
- `name`
- `image_url`
- `price`
- `price_label`
- `food_type`
  - `veg`
  - `non_veg`
- `is_spicy`
- `spicy_label`
- `popularity_label`
- `popularity_score`
- `is_available`


## 3. Root domain entities the homepage actually needs

From those fields, the homepage should be built on these root entities:

## 3.1 Customer context

Needed for:

- selected location
- address picker
- personalized feed later
- distance calculation
- ETA relevance

Root fields:

- `customer_id`
- `selected_address_id`
- `saved_addresses`
- `latitude`
- `longitude`
- `city`
- `area`


## 3.2 Restaurant

This is the core homepage entity.

Without restaurants, homepage is mostly decorative.

Root fields:

- identity
- branding
- operational state
- location
- cuisine/tags
- delivery capability
- rating/review summary
- promotional summary


## 3.3 Menu item

Needed for:

- popular foods
- recommended food cards
- later restaurant detail and cart

Menu items are a homepage dependency, not only a restaurant-detail dependency.


## 3.4 Category

Needed for:

- cuisine/category strip
- feed filtering
- navigation into restaurant/item subsets

But categories should be attached to real restaurant/item catalog data.


## 3.5 Promotion / banner

Needed for:

- hero promo carousel
- banner carousel
- offer-driven homepage merchandising

This should be its own content/merchandising domain.


## 3.6 Favorite state

Needed for:

- heart state on restaurant cards
- bookmark state on recommended items

This is a user-to-entity relationship domain.


## 4. Recommended backend modules for homepage

Based on the Flutter homepage, homepage should be supported by these backend modules:

## 4.1 Customer Context Module

Responsibilities:

- get current location context
- list saved addresses
- set selected address
- store geocoded location later


## 4.2 Restaurant Catalog Module

Responsibilities:

- restaurant listing
- restaurant card data
- distance/ETA projection
- open/closed status
- cuisine tagging


## 4.3 Menu Catalog Module

Responsibilities:

- menu item catalog
- featured items
- popular items
- item availability


## 4.4 Merchandising Module

Responsibilities:

- promo carousel
- banner placements
- homepage featured sections
- target routing for campaigns


## 4.5 Discovery Module

Responsibilities:

- categories
- filters
- homepage composition
- feed assembly
- search later


## 4.6 Favorites Module

Responsibilities:

- favorite restaurants
- favorite items later


## 5. Proposed homepage database structure

This is the recommended first-pass database design for homepage support.

## 5.1 `customer_addresses`

- `id`
- `customer_user_id`
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
- `is_default`
- `is_active`
- `created_at`
- `updated_at`


## 5.2 `restaurant_discovery_profiles`

This should sit beside restaurant core data or be merged into restaurant core if the system is still small.

- `id`
- `restaurant_id`
- `slug`
- `display_name`
- `cover_image_url`
- `logo_url`
- `short_description`
- `primary_cuisine_label`
- `rating_average`
- `review_count`
- `is_open`
- `supports_delivery`
- `has_free_delivery`
- `offer_text`
- `estimated_delivery_min_minutes`
- `estimated_delivery_max_minutes`
- `sort_rank`
- `is_featured`
- `is_active`


## 5.3 `categories`

- `id`
- `slug`
- `name`
- `icon_url`
- `sort_order`
- `is_featured`
- `is_active`


## 5.4 `restaurant_categories`

- `restaurant_id`
- `category_id`


## 5.5 `menu_items`

- `id`
- `restaurant_id`
- `category_id`
- `slug`
- `name`
- `description`
- `image_url`
- `price`
- `currency_code`
- `is_available`
- `food_type`
- `is_spicy`
- `is_featured`
- `is_popular`
- `popularity_score`
- `rating_average`
- `rating_count`
- `created_at`
- `updated_at`


## 5.6 `promo_banners`

- `id`
- `title`
- `subtitle`
- `image_url`
- `placement`
  - `home_carousel`
  - `home_banner`
- `target_type`
  - `restaurant`
  - `category`
  - `menu_item`
  - `url`
  - `none`
- `target_id`
- `cta_text`
- `sort_order`
- `is_active`
- `start_at`
- `end_at`


## 5.7 `user_favorite_restaurants`

- `user_id`
- `restaurant_id`
- `created_at`


## 5.8 `user_favorite_menu_items`

- `user_id`
- `menu_item_id`
- `created_at`


## 6. Recommended homepage API contract

Homepage should start with one aggregate endpoint:

### `GET /home/feed`

Recommended response:

```json
{
  "location_context": {
    "selected_address_id": 11,
    "location_title": "Ratnachowk",
    "location_subtitle": "Pokhara, Street No 14",
    "saved_addresses_count": 2
  },
  "promos": [],
  "categories": [],
  "filters": {
    "sort_options": [],
    "rating_options": [],
    "offer_options": [],
    "price_band_options": [],
    "time_options": []
  },
  "recommended_items": [],
  "popular_foods": [],
  "restaurants": []
}
```

Why aggregate first:

- mobile homepage is one composed experience
- frontend should not need 6 to 8 startup calls just to render the home screen
- backend can still source this from multiple modules internally


## 7. Dependency order for implementation

This is the cleanest order to build from basic upward.

## Phase 1: foundations

1. customer address / selected location support
2. restaurants
3. categories
4. restaurant-category mapping

This is enough to render:

- location header
- category strip
- basic restaurant list


## Phase 2: catalog enrichment

5. menu items
6. restaurant delivery metadata
7. rating/review summary fields

This is enough to render:

- recommended items properly
- popular foods properly
- richer restaurant cards


## Phase 3: merchandising

8. promo banners
9. homepage placements

This is enough to render:

- promo carousel
- banner carousel


## Phase 4: aggregation

10. `GET /home/feed`
11. filters
12. search


## 8. Important design corrections from the Flutter app

## 8.1 Recommended cards are not really restaurants

The Flutter app currently reuses `RestaurantEntity` for a food-style recommended card.

That should not drive backend design.

Correct backend design:

- keep restaurant entity for restaurants
- create item/featured-item payloads for food cards


## 8.2 Categories should not be standalone decoration

Categories need meaningful mapping to:

- restaurants
- menu items

Otherwise they are only icons and labels.


## 8.3 Homepage depends on real location context

Distance, ETA, restaurant relevance, and delivery availability all become better once selected address or approximate map location is real.

So location is not a later cosmetic feature. It is part of the homepage root context.


## 8.4 Promotions should be their own subsystem

Banners and carousels should not be embedded ad hoc inside restaurants or categories.

They need:

- placement
- scheduling
- target routing
- ordering


## 9. Final recommendation

If we start from homepage properly, the first real backend work after auth should be:

1. customer addresses / selected location
2. restaurant discovery profiles
3. categories and mappings
4. menu items
5. promo banners
6. homepage feed aggregator

That is the clean root-first architecture implied by the Flutter app.
