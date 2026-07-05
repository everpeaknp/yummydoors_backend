# YummyDoors Reservations Backend Plan

This doc tracks the table-booking backend based on the current
`yummydoors_mobile` flow.

## Flutter Flow We Matched

Current mobile booking flow:

1. `restaurant_detail_page.dart` exposes `Book a Table`
2. `book_table_page.dart` collects:
   - customer name
   - phone
   - guest count
   - date
   - time slot
3. `select_table_page.dart` expects:
   - table grid
   - table status: `available`, `booked`, `selected`
   - table grouping by category/tab:
     - `All`
     - `Indoor`
     - `Outdoor`
     - `Terrace`
     - `Private`
4. `table_reservation_success_page.dart` expects:
   - reservation id
   - name
   - mobile number
   - table number
   - number of guest
   - time
   - date
   - floor
   - occasion

## Backend Done In This Slice

Customer-side:

- public availability endpoint now accepts:
  - `reservation_date`
  - `guest_count`
  - optional `reservation_time`
- availability response now includes:
  - slot list
  - eligible tables
  - per-table inventory status for a selected slot
- reservation create now supports:
  - guest count
  - selected table
  - contact name
  - contact phone
  - contact email
  - `occasion`
  - special request
- reservation response now includes:
  - reservation code
  - selected table label
  - selected table zone
  - occasion
  - cancellation reason
  - status events

Merchant/admin-side:

- list reservation tables for a restaurant
- create reservation table
- update reservation table
- delete reservation table
- list restaurant reservations
- get restaurant reservation detail
- update restaurant reservation status
- assign/reassign table while updating status

## API Surfaces Added Or Extended

Public/customer:

- `GET /api/v1/restaurants/{slug}/reservations/availability`
- `POST /api/v1/restaurants/{slug}/reservations`
- `GET /api/v1/reservations`
- `GET /api/v1/reservations/{reservation_id}`
- `POST /api/v1/reservations/{reservation_id}/cancel`

Merchant/admin:

- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables`
- `POST /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables`
- `PUT /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `DELETE /api/v1/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}`
- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservations`
- `GET /api/v1/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}`
- `POST /api/v1/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}/status`

## Important Mapping Notes

- Flutter `table category` maps cleanly to backend table `zone`
- Flutter `table number` can use backend table `label` or `code`
- Flutter `floor` can use backend table `zone`
- Flutter `occasion` is now a first-class reservation field
- Merchant and ops admins share the same management endpoints because backend
  access checks already allow `super_admin` and `ops_admin`

## Still Missing After This Slice

These are still not done yet:

1. real reservation time-slot rules per weekday or per special schedule
2. dining duration / overlapping seat-turn logic
3. pre-order attached to reservation
4. merchant reservation dashboard UI in desktop/admin
5. mobile API wiring to replace the current mock cubits/pages
6. reservation analytics and notification flows

## Recommended Next Step

Build the next reservation-specific layer before jumping to another domain:

1. weekday service schedule model
2. table-zone aware availability rules
3. reservation note + occasion editor in merchant UI
4. desktop merchant reservation inbox
