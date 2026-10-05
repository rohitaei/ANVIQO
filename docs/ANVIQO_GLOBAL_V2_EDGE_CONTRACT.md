# ANVIQO Edge Connector Contract

The edge connector is a read-only adapter, not a control gateway.

## Observation contract
Each observation should normalize to:
- tenant/organization_id
- plant_id
- area/unit/equipment identity when available
- tag
- timestamp UTC
- value
- engineering unit
- quality
- source protocol
- source address
- sequence/event time when available

## Supported connector families
- Siemens S7
- OPC UA
- MQTT/Sparkplug
- Modbus TCP
- CSV/JSON/XLSX/document import

## Reliability
The edge must support local buffering/store-and-forward, reconnect handling, duplicate protection, clock validation and explicit data-quality states.

## Security
Only outbound authenticated TLS connections to the cloud are permitted by the reference architecture. No inbound public OT connection.

## Safety
No write methods are part of the V2 observation contract.
