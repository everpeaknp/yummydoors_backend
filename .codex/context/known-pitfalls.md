# Known Pitfalls

- Repo boundary drift: this backend repo is often confused with `../yummydoors_desktop`.
- "Done in backend" does not mean visible in desktop or admin.
- Desktop can fail on prod-origin requests because of frontend state or auth issues, not necessarily missing backend routes.
- Swagger grouping can look odd if tags are mismatched even when routes exist.
- Server env updates do not apply until the Docker app container is recreated.
- Cloudinary failures are often env or package import problems, not UI issues.
- Google Maps issues belong to desktop/mobile env and Google Cloud project settings, not this backend unless geocoding is server-side.
