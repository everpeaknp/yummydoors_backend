# YummyDoors Reservation Parity

This document tracks reservation-management parity across:

- `yummydoors_backend`
- `yummydoors_desktop`
- `yummydoors_admin`
- `yummydoors_mobile` mock booking flow

## Product Intent

The mobile flow already shows the intended reservation journey:

1. Customer opens a restaurant detail page.
2. Customer taps `Book a Table`.
3. Customer fills:
   - name
   - phone
   - guest count
   - date
   - time
4. Customer selects a table from grouped availability.
5. Customer reaches a reservation success state with:
   - reservation id
   - table number
   - guest count
   - date/time
   - floor/zone
   - occasion

That means the web surfaces need two operational layers:

- merchant-facing reservation operations
- super-admin fallback reservation operations

## Backend Ready Now

The backend already supports the reservation foundation needed by web and later Flutter integration.

### Customer reservation APIs

- `GET /api/v1/restaurants/{slug}/reservations/availability`
- `POST /api/v1/restaurants/{slug}/reservations`
- `GET /api/v1/reservations`
- `GET /api/v1/reservations/{reservation_id}`
- `POST /api/v1/reservations/{reservation_id}/cancel`

### Merchant reservation APIs

- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables`
- `POST /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables`
- `PUT /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `DELETE /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservations`
- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}`
- `POST /api/v1/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}/status`

### Admin reservation APIs

These were added so admin is not blocked behind merchant-only routes:

- `GET /api/v1/admin/restaurants/{restaurant_id}/reservation-tables`
- `POST /api/v1/admin/restaurants/{restaurant_id}/reservation-tables`
- `PUT /api/v1/admin/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `DELETE /api/v1/admin/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `GET /api/v1/admin/restaurants/{restaurant_id}/reservations`
- `GET /api/v1/admin/restaurants/{restaurant_id}/reservations/{reservation_id}`
- `POST /api/v1/admin/restaurants/{restaurant_id}/reservations/{reservation_id}/status`

### Reservation payload data already available

- reservation code
- reservation status
- reservation date/time
- guest count
- customer contact data
- occasion
- special request
- cancellation reason
- selected table object
- selected table label and zone
- status event timeline

### Table payload data already available

- code
- label
- zone
- min guest count
- max guest count
- seat capacity
- derived category
- status
- sort order

## Desktop Parity

### Was missing before

- no merchant reservation queue page
- no merchant table inventory page
- no direct reservation entry in merchant navigation

### Now covered

- merchant dashboard links to:
  - reservation queue
  - reservation tables
- user menu includes direct `Reservations` entry when merchant-ready
- `yummydoors_desktop` now has:
  - `/merchant/reservations`
  - `/merchant/tables`

### What desktop reservation queue now does

- list reservations for active merchant restaurant
- filter by date and status
- show summary counts
- inspect a reservation in detail
- assign a matching table
- add operational note
- move status through merchant workflow
- show reservation timeline/events

### What desktop table inventory now does

- list current reservation tables
- create table
- edit table
- delete table
- manage zone, guest window, status, and sort order

## Admin Parity

### Was missing before

- no admin reservation page
- no admin reservation routes in backend
- no reservation entry in admin sidebar/dashboard

### Now covered

- `yummydoors_admin` now has `/reservations`
- admin sidebar includes `Reservations`
- admin dashboard links into reservation ops
- admin page can:
  - select restaurant
  - inspect reservation queue
  - filter by date and status
  - inspect reservation detail
  - assign table
  - move reservation status
  - create/edit/delete reservation tables

## Mobile Mock Flow Mapping

Current mobile mock expects these backend-aligned concepts:

### Book table page

- customer identity fields
- guest count
- date
- time

### Select table page

- grouped table inventory
- available vs booked vs selected states
- tabs like `All`, `Indoor`, `Outdoor`, `Terrace`, `Private`

### Success page

- reservation id/code
- table label/number
- guest count
- date/time
- zone or floor
- occasion

## Remaining Gaps

These still remain after the current backend plus desktop/admin work.

### Backend gaps

- no public restaurant reviews write-flow yet
- no payment-gateway-backed reservation deposit/prepay flow
- no notification pipeline for reservation confirmations/reminders
- no admin aggregate reservation analytics endpoint yet

### Mobile integration gaps

- Flutter still needs real repository/data-source wiring
- Flutter still needs real availability fetch
- Flutter still needs real reservation create
- Flutter still needs real reservation history/detail
- Flutter still needs real table inventory mapping into its tab UI

### UX parity gaps

- mobile mock has richer visual table-zone grouping than current web surfaces
- desktop/admin still use operational forms, not final polished restaurant-host UI
- customer-facing web reservation flow is not built yet

## Recommended Next Steps

1. Wire Flutter booking flow to the live reservation endpoints.
2. Add restaurant-level table-zone grouping metadata if mobile wants stronger `Indoor/Outdoor/Terrace/Private` tabs.
3. Add reservation notifications:
   - confirmation
   - reminder
   - cancellation
4. Add admin reporting:
   - bookings per restaurant
   - no-show rate
   - slot occupancy
5. Add customer-facing web reservation history and cancellation page if desktop customer parity becomes a priority.
