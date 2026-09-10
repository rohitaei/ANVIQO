# ANVIQO Plant-Scoped Authentication V1

ANVIQO now supports plant-scoped user authentication on top of the existing Phase 2 tenant foundation.

## Login model

`/login` now accepts:
- Plant ID / Site
- Username
- Password

A user is admitted only when the credentials are valid **and** the user has an ACTIVE membership for that plant.

## Isolation

The authenticated session carries:
- organization_id
- plant_id
- role
- username

Plant access is therefore membership-scoped. A user assigned to Plant A cannot authenticate into Plant B unless a separate active membership exists.

## Provisioning

Organization ADMIN/OWNER users can provision a plant user through:
- `POST /api/admin/plant-users`

Required JSON fields:
- `username`
- `password`
- `plant_id`

Optional:
- `display_name`
- `role` (`OWNER`, `ADMIN`, `ENGINEER`, `OPERATOR`, `VIEWER`)

Passwords are stored as salted scrypt hashes, never plaintext.

## Session endpoints

- `GET /api/session/context` — current authenticated organization/plant/role.
- `GET /api/my-plants` — active plants assigned to the current user.

## Safety

This layer is authentication, authorization and tenant context only. It does not modify V5 intelligence and does not enable PLC writes, SCADA control, automatic authorization, or automatic execution.

## Universal platform direction

The intended model is:

`Organization -> Plant -> User -> Membership -> Role -> Plant-scoped ANVIQO`

This supports multiple plants without duplicating the frozen V5 reasoning engine.
