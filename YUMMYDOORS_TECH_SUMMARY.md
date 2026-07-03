# YummyDoors Tech Summary

This document captures the current high-level technical direction discussed for the YummyDoors product.

## Product split

YummyDoors is planned as a separate product surface from the existing Yummy POS system.

- Customer-facing mobile app: `Flutter`
- Restaurant dashboard / admin / operations panel: `Next.js`
- YummyDoors backend: separate `FastAPI` service
- Existing POS backend: separate `FastAPI` service that remains independent

The intended communication model is:

- YummyDoors talks to POS through APIs
- POS remains its own backend and business domain
- YummyDoors owns its own app workflows and customer-facing logic

## Core stack

### Frontend

- `Flutter` for the customer app
- `Next.js` for the restaurant/admin web panel

### Backend

- `FastAPI` for the YummyDoors backend
- `Celery` for background jobs
- `WebSockets` for realtime features

### Data and state

- `PostgreSQL` as the primary relational database
- `Redis` for cache, ephemeral state, and async/job support

### Media and files

- `Cloudinary` or object storage for uploaded media and file handling

### Auth and notifications

- `Firebase Auth`
- `Firebase Notifications`
- JWT-based backend authorization flow where needed between client and backend

### External integrations

- Yummy POS API
- Payment gateway
- Map / location service

### Mapping direction

The budget-conscious mapping direction discussed was:

- `MapLibre`
- OpenStreetMap-based map stack
- lower-cost routing and geocoding approach instead of going Google-first

## Architecture direction

The agreed direction was not microservices first.

The preferred structure is:

- separate YummyDoors backend
- separate Yummy POS backend
- API-only communication between them
- modular monolith approach for YummyDoors in the first phase

This means YummyDoors should start as one well-structured backend application with clear internal modules, instead of splitting too early into many deployable services.

## Core YummyDoors backend modules

The modules discussed for the YummyDoors backend were:

- Auth
- Users
- Restaurants
- Menus
- Cart
- Orders
- Delivery
- Tracking
- Notifications
- Offers / Loyalty
- POS Integration
- Webhooks

## One-line summary

The decided direction was:

`Flutter + Next.js + FastAPI + Celery + WebSockets + PostgreSQL + Redis + Cloudinary/Object Storage + Firebase Auth/Notifications + MapLibre/OpenStreetMap`

with:

- a separate YummyDoors backend
- a separate existing POS backend
- API-only integration between them
- a modular monolith architecture for the YummyDoors backend in the first phase

## Practical meaning

In practical terms, this setup aims to give:

- fast product delivery without premature microservice overhead
- clear separation between customer delivery workflows and POS workflows
- enough realtime support for tracking and operational updates
- enough background processing for jobs like notifications, sync, and scheduled tasks
- flexibility to evolve later if product scale demands service splitting

## Notes

- This is a high-level tech summary, not a deployment spec.
- This does not replace API contracts, schema docs, or sprint implementation plans.
- If needed, this can be expanded into:
  - system architecture diagram
  - module ownership breakdown
  - deployment topology
  - Sprint 1 implementation checklist
