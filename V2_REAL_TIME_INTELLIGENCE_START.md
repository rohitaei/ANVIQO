# ANVIQO V2 - Real-Time Industrial Intelligence

Status: V2 REAL-TIME INTELLIGENCE FOUNDATION COMPLETE

## Frozen boundary

V5 remains frozen and read-only.

- PLC write: FALSE
- SCADA control: FALSE
- Automatic authorization: FALSE
- Automatic execution: FALSE
- Human decision required: TRUE
- V5 reasoning is reused, not duplicated.

## Universal architecture

Any Plant
-> Universal onboarding / normalized data
-> read-only source adapters
-> V2 Real-Time Data Fabric
-> evidence trust / freshness
-> WATCH / discovery orchestration
-> Equipment DNA context
-> existing V5 Frozen Intelligence
-> human decision
-> Plant Memory
-> ROI

The V2 layer is plant-universal. Plant-specific tags, thresholds, process rules, prediction logic, diagnosis logic, or control logic are not embedded in V2. The design principle remains **CHANGE DATA, NOT CODE**.

## Completed V2 sequence

### Alpha 1.1 - Source Adapter + Data Fabric

Delivered:

1. Normalized IndustrialPoint contract.
2. Bounded plant-scoped, tag-scoped read-only stream buffer.
3. Data-path health reporting.
4. Transport-neutral read-only source adapter interface.
5. Existing PCI demo-stream adapter using the existing simulator only.
6. FabricSourceRunner for one-shot source -> fabric polling.

No OPC UA/MQTT/Historian client is activated by the demo adapter.

### Alpha 1.2 - Data Trust / Freshness

Delivered:

- Freshness states: FRESH, AGING, STALE, EXPIRED, INVALID, FUTURE.
- Evidence trust states: TRUSTED, DEGRADED, LIMITED, UNTRUSTED.
- Quality handling for GOOD, DEGRADED, BAD, UNKNOWN.
- BAD, invalid, future, and expired evidence is rejected.
- Stale evidence can remain visible but is explicitly marked stale.
- Trust is evidence gating/metadata only; it is not a reasoning engine.

### Alpha 1.3 - Live Plant Brain

Delivered:

- Universal tenant-scoped observation over the V2 fabric.
- Trusted / limited / untrusted evidence accounting.
- Fresh / stale evidence accounting.
- Existing V5 intelligence can be invoked through an explicit bridge.
- No replacement plant-health, prediction, diagnosis, or root-cause engine.

### Alpha 1.4 - WATCH + discovery orchestration

Delivered:

- Generic value-change and evidence-quality/freshness observation.
- States: INSUFFICIENT_EVIDENCE, WATCH, OBSERVE.
- WATCH candidates are discovery prompts, not anomaly, alarm, diagnosis, prediction, or failure verdicts.
- No plant-specific thresholds or process rules.

### Alpha 1.5 - Equipment DNA

Delivered:

- Universal plant-scoped equipment nodes.
- Supplied equipment relationships.
- Exact-tenant context lookup.
- No invented topology or process semantics.
- Context is evidence for existing V5 intelligence.

### Alpha 1.6 - Live event context

Delivered:

- Joins WATCH candidates with tenant-scoped Equipment DNA.
- Preserves an existing V5 What Changed/Event result when supplied.
- No cross-plant fallback.
- Read-only and human-governed safety contract preserved.

### Alpha 1.7 - Live V2 -> existing V5 event bridge

Delivered:

- Tenant-scoped live change evidence and Equipment DNA are passed to an injected existing V5 handler.
- Without a handler, V2 reports NOT_INVOKED instead of creating replacement reasoning.
- Existing V5 event intelligence remains authoritative.

### Alpha 1.8 - Tenant-safe V5 What Changed adapter

Delivered:

- Explicit adapter to the existing V5 build_plant_what_changed implementation.
- Area evidence with a mismatched plant_id is rejected.
- Existing V5 remains the only What Changed / health / event-correlation engine.

### Alpha 1.9 - Tenant-safe live V5 evidence bridge

Delivered:

- Area evidence is obtained from an explicit tenant-scoped provider.
- Provider is called only with context.plant_id.
- Returned evidence must carry the same plant_id.
- Empty evidence remains empty; no global fallback.

### Alpha 1.10 - Live V2 -> V5 orchestration seam

Delivered:

- run_live_v5_pipeline() joins WATCH, Equipment DNA, live event context, and existing V5 What Changed.
- Watch context and requested plant identity must match.
- Existing V5 reasoning remains authoritative.

### Alpha 1.11 - Universal tenant evidence provider

Delivered:

- TenantEvidenceProvider adapts the existing universal onboarding package into tenant-scoped V5-compatible evidence.
- Only explicit health_score/status evidence is forwarded.
- V2 never invents plant health from raw records.
- Cross-plant package requests are rejected.
- Safety remains read-only and human-governed.

### Alpha 1.12 - Discovery orchestration

Delivered:

- Generic WATCH candidates are converted into discovery candidates.
- Classification is DISCOVERY_CANDIDATE.
- Discovery does not declare anomaly, alarm, diagnosis, or failure.
- Exact plant scope and safety are preserved.

### Alpha 1.13 - Alarm bridge

Delivered:

- Explicit supplied alarm evidence can be normalized and passed to an existing V5 handler.
- V2 does not create alarm thresholds or alarm decisions.
- Tenant scope and read-only safety are enforced.

### Alpha 1.14 - PT-303 pressure demonstration

Delivered:

- Deterministic read-only PT-303 demonstration harness.
- Uses explicit tenant evidence.
- Reuses the live V2 -> existing V5 pipeline.
- Accepts a supplied verified-history callback.
- Requires human verification.
- No automatic control or repair action is performed.

The PT-303 demo is a demonstration harness, not a plant-specific reasoning engine. PT-304 can use the same universal seam by changing supplied data/evidence rather than adding plant-specific code.

## Verification

The dedicated **ANVIQO V2 Regression Tests** workflow passed on the latest V2 implementation commit.

The V2 regression suite covers:

- normalization and data-fabric behavior
- tenant isolation
- trust/freshness
- Plant Brain orchestration
- WATCH/discovery behavior
- Equipment DNA context
- live event context
- V2 -> existing V5 What Changed bridging
- tenant evidence
- alarm bridge
- PT pressure demo
- read-only / human-governed safety contracts

Unrelated legacy/phase certification workflows are tracked separately and are not used as the V2 regression verdict.

## V2 architectural guarantees

1. **Universal:** plant data/configuration changes; V2 intelligence code does not become plant-specific.
2. **Tenant-safe:** no cross-plant fallback or substitution.
3. **Evidence-first:** stale, invalid, bad, future, or missing evidence is explicitly represented.
4. **V5 reuse:** existing V5 health, What Changed, event correlation and other frozen intelligence remain authoritative.
5. **No duplicate reasoning:** V2 adds transport, evidence gating, orchestration and context seams only.
6. **Human governed:** no automatic authorization, execution, PLC write, or SCADA control.
7. **Read-only:** all V2 source/demo paths preserve the safety boundary.

## Next roadmap phase

V2 Real-Time Industrial Intelligence foundation is complete at the current universal orchestration scope.

Future capabilities such as live production connectors, richer predictive intelligence, autonomous investigation, enterprise ROI, or expanded Command Centre behavior must be implemented as separate milestones and must continue to reuse the frozen V5 intelligence rather than creating duplicate reasoning engines.
