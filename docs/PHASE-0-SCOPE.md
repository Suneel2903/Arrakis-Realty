# Phase 0 scope (Weeks 1–2)

## Customer
- Website: home, how it works, live project page (gallery, floor plans, price list, payment plan, amenities, RERA no.), policy pages.
- Phone OTP sign-in (Firebase) with per-purpose consent and 18+ confirmation.
- Paid access via Razorpay; on success, unlock project details and selected areas. Receipt by email and WhatsApp.
- WhatsApp: OTP template, welcome, payment confirmation, advisor connect.

## Admin
- Staff users with roles: Super admin, Admin, Sales manager, Sales executive (pre-sales). Email + TOTP.
- Projects and units: create, Excel import using the client template with row-level validation report, media upload (images, video, PDFs).
- Leads: list + detail, 10 stages, notes, owner, source campaign (UTM/gclid/fbclid), what the customer viewed, payment status.
- Pre-sales sees only assigned leads; manager sees all and can reassign.
- Meta and Google lead-form webhooks create leads.
- Audit log (who, what, before, after) on every admin write.

## Out of scope for Phase 0
Map UI, research desk, refunds automation, bookings, ads spend dashboard.
