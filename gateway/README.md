# ANVIQO Read-only PLC Gateway

## Architecture

Siemens S7-400 in the plant LAN → customer-approved OPC UA server / industrial edge gateway in the OT DMZ → outbound HTTPS → ANVIQO /api/gateway/v1/telemetry → tenant-scoped PostgreSQL → authenticated /api/plc/live.

Never connect a public cloud service directly to a PLC. The edge gateway must be approved by plant OT/IT. Firewall policy should allow OPC UA only between the gateway and approved in-plant OPC UA server, and outbound HTTPS only from gateway to the approved ANVIQO hostname. No inbound internet route to the PLC.

## ANVIQO staging configuration

Set these secrets on the ANVIQO service only after confirming the exact customer tenant:

- ANVIQO_PLC_INGEST_ORG_ID: exact existing organization ID
- ANVIQO_PLC_INGEST_PLANT_ID: exact existing plant ID
- ANVIQO_PLC_INGEST_TOKEN: long random bearer token (at least 32 random bytes)
- ANVIQO_PLC_ALLOWED_TAGS: comma-separated allowlist of exact onboarded tag IDs

The server binds the gateway credential to exactly one configured organization and plant. Tenant identity is not accepted from gateway payloads. The ingress route remains disabled until all four variables are configured. Never reuse the ANVIQO administrator password.

## Edge gateway installation

Use a customer-managed Linux industrial PC/IPC in the approved OT/DMZ zone. Install Python 3.10+ and run:

    python -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    cp tags.example.json tags.json

Set environment variables:

- ANVIQO_OPCUA_ENDPOINT: approved OPC UA server endpoint (not PLC IP unless OT explicitly approves)
- ANVIQO_OPCUA_USERNAME and ANVIQO_OPCUA_PASSWORD: read-only OPC UA account, if required
- ANVIQO_OPCUA_SECURITY_STRING: approved SignAndEncrypt certificate configuration; do not disable certificate checks
- ANVIQO_INGEST_URL: ANVIQO HTTPS base URL
- ANVIQO_PLC_INGEST_TOKEN: gateway token
- ANVIQO_GATEWAY_ID: unique gateway name
- ANVIQO_TAG_MAP: path to the approved tag mapping JSON
- ANVIQO_POLL_SECONDS: default 2 seconds

Run python anviqo_opcua_gateway.py under a supervised service only after OT acceptance and bench testing.

## Tag map

Replace example NodeIds with exact NodeIds exposed by the approved OPC UA server. Tag names must match the selected plant's onboarded PCI tag identity and server-side allowlist. Units must come from approved engineering data, never guessed from PLC register addresses.

## Data quality and safety

- Numeric values only; every point carries OPC UA quality and source timestamp.
- Bad/uncertain quality is retained but never marked fresh/healthy.
- A point is fresh only when received within 10 seconds and quality is GOOD.
- Server rejects malformed tags, timestamps outside the accepted clock window, oversized batches and unauthenticated requests.
- Older source timestamps cannot overwrite newer values.
- Storage is keyed by organization + plant + tag.
- Live read endpoint requires an authenticated user in the exact tenant/plant.
- No PLC write, SCADA control, OPC UA write, method invocation or automatic authorization exists in this connector.

## Commissioning checklist

1. Confirm OT/IT approval, network zone, firewall path and customer change record.
2. Confirm S7-400 CPU/network details and approved OPC UA server or gateway model.
3. Create a read-only OPC UA account and verify write access is denied at the OPC UA server itself.
4. Export an approved NodeId/tag/unit map; verify raw values, scaling and units against calibrated references.
5. Configure the four ANVIQO tenant secrets securely.
6. Bench-test with simulator first; verify quality, timestamps, units, stale detection and tenant isolation.
7. Conduct a plant-approved read-only test window; compare a small approved tag set with local HMI/PLC diagnostics.
8. Only after sign-off, widen the approved tag list. Never enable PLC/SCADA writes.

Current status: software connector scaffold only. No physical PLC session or customer telemetry has been established by this repository change.
