# x402 Canonical Domain Discovery Specification

**Working Group Proposal: Domain Discovery via RFC 8615 Well-Known Manifest**  
**Status**: Standards Track Proposal  
**Authors**: Corrente Labs, Inc., x402 Foundation Domain Discovery Working Group  
**Target Registry**: IANA Well-Known URIs (`/.well-known/x402`)  
**RFC 2119 / BCP 14 Conformance**: Key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in BCP 14.

---

## 1. Abstract & Motivation

Autonomous AI agents and automated HTTP clients require a fast, deterministic, and cryptographically verifiable mechanism to discover payment requirements and supported settlement rails before invoking monetized web endpoints.

Prior exploratory drafts contemplated a "two-lane" discovery pattern—splitting discovery between a minimal root entry and an external OpenAPI 3.1 specification carrying bespoke `x-x402` vendor extensions. Under that model, agents were expected to traverse two parallel discovery paths: reading root metadata in Lane 1, then fetching, parsing, and resolving route-level payment terms inside OpenAPI documents in Lane 2.

This specification documents why **the two-lane model is fundamentally unworkable in production**, and formally establishes the **Single-Lane Canonical x402 Domain Discovery Standard**. Grounded in IETF RFC 8615, discovery resolves through a single authoritative manifest served at `/.well-known/x402`. It co-locates resource routes, accepted settlement schemes, CAIP-2 blockchain networks, assets, amounts, and cryptographic signing keys in one atomic, cacheable payload. OpenAPI descriptions remain fully supported as an optional, informational documentation link—ensuring human developer documentation never obstructs or complicates autonomous machine payment negotiation.

---

## 2. Empirical Analysis: The Failure of the Two-Lane Model vs. Single-Lane Invariants

Extensive conformance testing and empirical network data demonstrate why splitting discovery across two lanes fails both architectural and operational requirements:

### 2.1 The Split-Brain Vulnerability & Cache Drift
In a two-lane architecture, an origin host publishes root metadata at `/.well-known/x402` (Lane 1) and operation-level terms inside an external OpenAPI document via `x-x402` overlays (Lane 2). 

Because these two artifacts are hosted, cached, and invalidated independently, **cache drift is mathematically inevitable**:
* An origin server may update route pricing or deprecate a payment rail in its backend API carrier.
* A downstream CDN edge, reverse proxy, or local client cache may continue serving a stale OpenAPI JSON bundle for hours or days.
* As a result, an autonomous agent resolving terms via Lane 2 constructs a payment payload that the origin server (enforcing Lane 1) rejects with an unexpected HTTP 402 or 400 error. In the worst case, divergent terms lead to irrecoverable payment discrepancies and financial dispute.

**The Single-Lane Resolution**: By enforcing a single manifest at `/.well-known/x402`, payment terms exist in exactly one place. Edge caches revalidate a single atomic document via standard `ETag` and `If-None-Match` HTTP semantics, guaranteeing zero split-brain divergence.

### 2.2 Production Census & Single-Document Topology
Empirical measurements of live `/.well-known/x402` deployments (`meloliva14/x402-measure`) highlight two distinct realities:
* **Single-Document `resources` Topology vs. Mandatory `openapi` Arrays**: In the 775-manifest snapshot evaluated against mandatory `openapi` entry rules, **0 out of 775 manifests** published an `openapi` array, whereas **649 out of 775** already used a single-document `resources` array at `/.well-known/x402`.
* **Intentional `x402Version: 2` Schema Break (§8.2 / §8.3)**: In the 2026-10-14 census (`2d49c52`, 773 JSON responses at `/.well-known/x402`), **758 of 773 documents** carry legacy top-level keys (`version`, `description`, `name`) or informal `{url, method}` resource entries, with **1 of 773** validating unmodified against this specification's strict schema (`additionalProperties: false` and `required: ["path", "accepts"]`).

Accordingly, the single-lane model preserves the established single-document `resources` deployment topology at `/.well-known/x402` while enforcing the intentional, normative `x402Version: 2` schema boundary and migration path specified in §8.2 and §8.3.

### 2.3 Prohibitive Agent Latency & Parser Complexity
Autonomous agents operate on sub-100ms request/response cycles:
* In a two-lane model, an agent must: (1) fetch the root manifest, (2) extract the OpenAPI URL, (3) fetch an external 200KB–500KB OpenAPI JSON bundle, (4) parse and recursively resolve `$ref` JSON Pointers across multi-file schemas, and (5) traverse operation paths to locate `x-x402` vendor blocks.
* This introduces multi-roundtrip network latency, substantial memory consumption, and brittle third-party parsing dependencies into lightweight agent execution runtimes.

**The Single-Lane Resolution**: The canonical manifest is self-contained (`<2KB` baseline for minimal or facilitator origins, scaling linearly $O(N)$ at `~150–215 bytes/entry` raw for route metadata plus inlined `accepts[]` terms—or **`~3.6–3.7KB` compressed on the wire (`gzip -9`) for a complete 75-route single-enumeration catalogue**). An agent reads it in a single atomic HTTP GET, evaluates available settlement schemes in sub-millisecond memory lookups, and dispatches the paid request immediately.

### 2.4 Cryptographic Ground Truth & Verification Impossibility
Under zero-trust execution, an agent must cryptographically verify that the payment requirements it received were signed by the domain owner and not injected by an adversarial proxy or rogue CDN node:
* In a two-lane architecture, verifying terms requires computing canonical digests across a mutable graph of distributed documents (the root manifest plus all linked OpenAPI documents and external overlays). Any dynamic change or formatting difference breaks the cryptographic signature.
* In the single-lane architecture, the manifest contains host-level public keys (`keys`) that are directly cross-validated against public DNS TXT records (`_x402key.<domain>`). The manifest is canonically hashed (RFC 8785 JCS) and verified in one self-contained step.

---

## 3. Core Architectural Invariants

### 3.1 Single Source of Truth
Payment discovery MUST resolve through a single authoritative manifest. Hosts MUST NOT require clients to reconcile conflicting or fragmented pricing terms across disparate endpoints. All runtime parameters necessary for an agent to construct an x402 payment challenge response (scheme, network, asset, and price) are declared directly in the manifest.

### 3.2 Universal Rail Neutrality
The discovery specification is transport- and settlement-rail agnostic. All supported blockchain networks are declared using canonical [CAIP-2](https://github.com/ChainAgnostic/CAIPs/blob/main/CAIPs/caip-2.md) identifiers (e.g. `eip155:8453`, `eip155:14`, `xrpl:0`, `stellar:pubnet`, `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp`). No single chain, token, or virtual machine is given preferential or hardcoded treatment.

### 3.3 Cryptographic Ground Truth, Stateless Off-Chain DNS Binding & Declarative Indexing
To prevent man-in-the-middle tampering, reverse-proxy spoofing, and edge-cache poisoning, hosts MAY advertise cryptographic public signing keys (`keys`) within the manifest. Clients verify manifest authenticity against authoritative public DNS TXT ground truth records published at `_x402key.<domain>`. Discovery and key verification MUST be executable strictly via standard HTTP GET (`RFC 9110`) and off-chain DNS/DNSSEC resolution (`RFC 4035` / `RFC 8615`) without requiring on-chain smart-contract state reads, ledger RPC queries, or paid on-chain storage/box rent. Discovery indexers and catalogues MUST ingest endpoints declaratively from `/.well-known/x402` and MUST NOT require prior on-chain settlement transactions (`pay-to-list` or merchant self-settlement) as a precondition for indexing.

### 3.4 Sub-Millisecond Agent Resolution, Compressed-Wire Budgeting & Single Normative Enumeration
Autonomous agents operate on tight latency budgets. For manifests in the **self-contained** resource class (`{path, accepts}`), a canonical `/.well-known/x402` manifest resolves in a single fetch governed by three empirical scaling rules:
1. **Per-Entry Scaling & Field-Set Bounds**: `<2KB` is the baseline footprint for a minimal origin or `facilitator`-only manifest (`0–4` resources). Multi-route resource-server catalogues scale linearly $O(N)$ within the same single document: route-level metadata (`path`, `methods`, `description`) accounts for `~150–215 bytes/entry` raw, rising to `~250–500 bytes/entry` raw when per-entry `accepts[]` objects (`scheme`, `network`, `asset`, `amount`/`maxAmount`, `recipient`) are inlined. Because per-route `path` and `description` values are unique high-entropy strings, per-route `resources[]` arrays re-serialized as **compact JSON (`separators=(',', ':')`)** compress at **`~3.6–3.9x` under `gzip -9`** across production content snapshots (for example, on the 75-route production manifest: `11,188 B` raw $\rightarrow$ `3,043 B` `gzip -9` (`3.68x`) at `updated: 2026-10-16T05:19:01Z` and `11,006 B` raw $\rightarrow$ `3,064 B` `gzip -9` (`3.59x`) at `updated: 2026-10-19T05:19:01Z` when compact-serialized with `separators=(',', ':')`, versus `13,559 B` raw $\rightarrow$ `3,118 B` `gzip -9` (`4.35x`) at `updated: 2026-10-19T05:19:01Z` when `resources[]` is measured exactly as served with indentation; for the complete single-enumeration document at `updated: 2026-10-16T05:19:01Z`, `15,150 B` raw $\rightarrow$ **`3,739 B` `gzip -9`** when pretty-printed with `indent=2`, or `12,578 B` raw $\rightarrow$ **`3,620 B` `gzip -9`** when compact-serialized with `separators=(',', ':')`).
2. **Compressed-Wire Budget vs. Raw-Byte Parser Limit**: Wire budgets are normative in **delivered compressed wire bytes (`<= 64KB` evaluated against the `Content-Encoding` actually delivered over HTTP, or against `gzip -9` when evaluating a static artifact offline)** alongside a `256KB` uncompressed parser safety ceiling. Evaluating against the delivered encoding is required because edge `gzip` and `br` (Brotli) configurations are not identical at small payload sizes, and compressed byte figures vary by `±0.1%` (`±3–5 B`) across same-width timestamp refreshes even when the uncompressed byte length (`35,315 B`) is unchanged (for example, delivering `5,714 B` $\rightarrow$ `5,709 B` under `Accept-Encoding: gzip` and `6,035 B` $\rightarrow$ `6,038 B` under default edge `Accept-Encoding: br` between the `2026-10-16T05:19:01Z` and `2026-10-17T05:19:02Z` snapshots). Expressing the primary operational budget in compressed wire bytes reflects real transport cost: human-readable pretty-printing increases raw size by `~24–25%` on a 75-route manifest (`+6,734 B` to `+7,115 B` raw) but adds **`< 200 B` (`~3%`, `+159 B` to `+196 B` `gzip -9`, `±0.1%`)** on the wire, whereas duplicating a 75-route enumeration increases raw size by `~57%` (`15,150 B` $\rightarrow$ `35,315 B` pretty-printed; `12,578 B` $\rightarrow$ `28,581 B` compact) and compressed wire weight by **`~35%`** (`+2,002 B`, `3,739 B` $\rightarrow$ `5,741 B` pretty-printed; `+1,925 B`, `3,620 B` $\rightarrow$ `5,545 B` compact on the `2026-10-16T05:19:01Z` snapshot, `±0.1%`).
3. **`resources[]` Is the Single Normative Route Enumeration ($O(N)$, Not $O(2N)$)**: Within `/.well-known/x402`, `resources[]` is the sole normative enumeration of monetized endpoints. Hosts MUST NOT split `resources[]` or `accepts[]` across paginated sub-documents, and SHOULD NOT duplicate a second parallel projection of the same route set (such as legacy `endpoints[]` or `services[]` arrays) inside `/.well-known/x402` or its `extensions` object. Where a host serves a secondary projection for non-x402 consumers (for example, a sibling `/.well-known/x402-service.json`), that projection SHOULD either be derived from `resources[]` or served at its own sibling URI; if retained inside `extensions` during migration, it counts against the `/.well-known/x402` compressed-wire budget.

---

## 4. Specification

### 4.1 Well-Known Entry Point
The host exposes its discovery manifest at the well-known URI:
```http
GET /.well-known/x402 HTTP/1.1
Host: example.com
```

* **Transport**: The endpoint MUST be served over TLS (`https://`). Unencrypted HTTP MUST NOT be used in production.
* **Content-Type**: The response MUST be served with `Content-Type: application/json`.
* **Path Registration**: The path complies with RFC 8615 under the IANA Well-Known URIs registry as `x402`.

### 4.2 Manifest Schema Definition

A compliant discovery manifest is a JSON object carrying the following properties:

| Field | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `x402Version` | `integer` | **REQUIRED**\* | Protocol version. MUST be `2`. (\*Required at the document root whenever `resources` is absent/empty or contains any `selfContainedResource` entry that omits its own `x402Version`; optional at the root when every `resources[]` entry is `pointerResource` or carries its own `x402Version: 2`). |
| `kind` | `string` or `array of strings` | **OPTIONAL** | Role of the host: `"resource-server"`, `"facilitator"`, or `"both"`. Defaults to `["resource-server"]`. |
| `resources` | `array of entries` | **REQUIRED**\* | List of payment-enabled resource entries (`selfContainedResource` or `pointerResource`). (\*Required for resource servers; optional for standalone/hybrid facilitators or transitional OpenAPI hosts). |
| `keys` | `array of objects` | **OPTIONAL** | Host cryptographic public verification keys. |
| `facilitator` | `string (URI)` | **OPTIONAL** | Canonical URI of an external facilitator used by this resource server. |
| `openapi` | `string` or `array of strings` | **OPTIONAL** | URI pointing to OpenAPI descriptions for developer documentation. Informational pointer; payment discovery resolves via `resources`. |
| `extensions` | `object` | **OPTIONAL** | Container for experimental, forward-compatible, or vendor-specific extension payloads without violating root schema determinism. |

**Client Tolerance of Unknown Root Keys vs. Publisher Strict Lint**: Compliant clients MUST ignore unrecognized descriptive root fields (such as `name`, `description`, `version`, or `contact`), while the schema explicitly forbids misplaced root-level payment carriers (`accepts`, `payTo`, `networks`, `fee`, `access`) via root `not.anyOf` constraints because those belong inside per-resource `accepts[]` objects. Publishers SHOULD place non-protocol descriptive metadata and forward-compatible extensions inside the `extensions` property bag, and publisher linters (`test_discovery.py`) enforce the strict root key set (`x402Version`, `kind`, `facilitator`, `keys`, `extensions`, `resources`, `openapi`).

### 4.3 Resource Entry Classes (`resources[]`: `self-contained` vs. `pointer`) & Effective Version Inheritance

Each entry in `resources[]` belongs to one of two explicitly named, structurally disjoint classes (`if`/`then`/`else` on `path`/`accepts` vs. `url`) that make distinct client guarantees:

#### Class 1: Self-Contained Resource Entry (`selfContainedResource` — `{path, accepts}`)
A **self-contained** entry declares both the relative endpoint path and its inline `accepts[]` settlement options (`additionalProperties: false`; MUST NOT carry `url`). A single manifest fetch answers path, price, network, asset, and payee (`recipient`), enabling pre-flighted payment resolution (§3) with zero per-route HTTP `402` probe roundtrips:

| Field | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `path` | `string` | **REQUIRED** | Relative path or URI template of the endpoint (e.g. `/api/v1/search`). |
| `accepts` | `array of objects` | **REQUIRED** | Non-empty list of accepted payment options for this resource. |
| `x402Version` | `integer` | **OPTIONAL**\* | Protocol version (`2`). Inherits the document root `x402Version` when omitted; required on the entry if the document root omits `x402Version`. |
| `description` | `string` | **OPTIONAL** | Human/agent readable summary of the resource capabilities. |
| `methods` | `array of strings` | **OPTIONAL** | Applicable HTTP methods (`["GET", "POST", ...]`). If omitted, applies to all methods. |

#### Class 2: Pointer Resource Entry (`pointerResource` — `{url, method?}` or URI String)
A **pointer** entry identifies a monetized endpoint by URL (`{"url": "https://...", "method"?: "GET", "methods"?: [...], "description"?: "...", "x402Version"?: 2}` with `additionalProperties: false` so it MUST NOT carry `path` or `accepts`, or a bare URI string). A pointer entry informs the client that the target URL is monetized; to learn the settlement terms (`scheme`, `network`, `asset`, `amount`, `recipient`) and authoritative runtime protocol version, the client MUST issue an HTTP request to `url` and parse its live HTTP `402` challenge. Because `selfContainedResource` (requires `path` + `accepts`, forbids `url`) and `pointerResource` (requires `url`, forbids `path` + `accepts`) are mutually exclusive, a client can deterministically classify every entry without ambiguity.

### 4.4 Payment Option Object (`accepts[]`)

Each payment option specifies an accepted settlement vehicle:

| Field | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `scheme` | `string` | **REQUIRED** | Settlement scheme: `"exact"`, `"upto"`, `"batch-settlement"`, or `"escrow"`. |
| `network` | `string` | **REQUIRED** | Canonical CAIP-2 identifier (`^[a-z0-9-]{3,8}:[-_a-zA-Z0-9]{1,32}$`). |
| `asset` | `string` | **OPTIONAL** | Token contract address, native currency symbol, or asset identifier. |
| `amount` | `string` | **OPTIONAL** | Fixed settlement amount in atomic units (`^[0-9]+$`). |
| `minAmount` | `string` | **OPTIONAL** | Minimum bounded settlement amount in atomic units (`^[0-9]+$`). |
| `maxAmount` | `string` | **OPTIONAL** | Maximum bounded settlement amount in atomic units (`^[0-9]+$`). |
| `recipient` | `string` | **OPTIONAL** | Destination payout address or account. |
| `extra` | `object` | **OPTIONAL** | Scheme-specific parameters (e.g. ledger timeout tolerances, memo hints). |

### 4.5 Cryptographic Verification Key Object (`keys[]`)

When manifest verification or challenge authentication is enforced:

| Field | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `kid` | `string` | **REQUIRED** | Key identifier matching the corresponding DNS TXT ground truth entry. |
| `alg` | `string` | **REQUIRED** | Signature algorithm (`"Ed25519"`, `"ES256"`, or `"ES256K"`). |
| `publicKey` | `string` | **REQUIRED** | Encoded public key bytes (hex or base64). |

---

## 5. Discovery Flow for Autonomous Agents

```
+------------------+         1. GET /.well-known/x402          +------------------+
|                  | ----------------------------------------> |                  |
| Autonomous Agent |                                           | Resource Server  |
|                  | <---------------------------------------- | (example.com)    |
|                  |       2. 200 OK (Canonical Manifest)      +------------------+
+------------------+
         |
         | 3. Match Target Endpoint (`resources[path]`)
         | 4. Select Supported Settlement Option (`accepts[scheme, network]`)
         v
+------------------+         5. Paid Request (x402 Headers)    +------------------+
| Autonomous Agent | ----------------------------------------> | Target Endpoint  |
|                  | <---------------------------------------- | (/api/v1/data)   |
|                  |           6. Settled Response             +------------------+
+------------------+
```

1. **Cold Discovery**: The agent fetches `https://<domain>/.well-known/x402`.
2. **Deterministic Evaluation**: The agent parses the single JSON object and filters `resources` for the desired URI path.
3. **Payment Option Negotiation**: For a `self-contained` entry (`{path, accepts}`), the agent matches its available settlement capabilities (e.g. EVM, Flare, XRPL, Stellar, Solana) directly against the resource's inline `accepts` array. For a `pointer` entry (`{url, method?}`), the agent sends a probe request to `url` to retrieve the live HTTP `402` challenge terms.
4. **Execution**: The agent issues the monetized request with the corresponding x402 payment payload, eliminating preliminary HTTP 402 challenge roundtrips whenever `self-contained` entries are published.

---

## 6. Security & Verification Considerations

### 6.1 DNS Ground Truth Cross-Validation
To verify that a discovery manifest has not been modified by an intermediary CDN edge or caching proxy:
1. The client inspects the manifest `keys` array for key identifier `kid`.
2. The client resolves the DNS TXT record for `_x402key.<domain>`:
   ```dns
   _x402key.example.com. IN TXT "v=x402key1; alg=Ed25519; k=d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
   ```
3. The client verifies that the public key declared in the HTTP manifest matches the public key anchored in authoritative DNS.

### 6.2 Cache Control & Freshness
Hosts SHOULD serve `/.well-known/x402` with appropriate HTTP caching headers:
* `Cache-Control: public, max-age=300, stale-while-revalidate=60`
* `ETag: "<canonical-jcs-hash>"`

Clients MUST honor standard HTTP cache revalidation semantics (`If-None-Match`), preventing stale term execution.

---

## 7. Conformance & Test Suite

The proposal is accompanied by a formal JSON schema and automated validation test harness:

* **JSON Schema**: [`proposal/domain-discovery.schema.json`](domain-discovery.schema.json)
* **Test Suite**: [`proposal/test_discovery.py`](test_discovery.py)
* **Positive Examples**:
  * [`examples/minimal.well-known-x402.json`](examples/minimal.well-known-x402.json)
  * [`examples/multirail-service.well-known-x402.json`](examples/multirail-service.well-known-x402.json)
  * [`examples/facilitator.well-known-x402.json`](examples/facilitator.well-known-x402.json)
  * [`examples/service-with-openapi.well-known-x402.json`](examples/service-with-openapi.well-known-x402.json)
  * [`examples/bare-openapi.well-known-x402.json`](examples/bare-openapi.well-known-x402.json)
  * [`examples/hybrid-facilitator.well-known-x402.json`](examples/hybrid-facilitator.well-known-x402.json)
  * [`examples/forward-extensions.well-known-x402.json`](examples/forward-extensions.well-known-x402.json)
  * [`examples/pointer-only-no-root-version.well-known-x402.json`](examples/pointer-only-no-root-version.well-known-x402.json)
* **Negative Edge Rejection Fixtures**:
  * `invalid-missing-version.json` (Missing required `x402Version`)
  * `invalid-bad-version.json` (Unsupported protocol version)
  * `invalid-version-conflict.json` (Root `x402Version: 2` conflicting with entry `x402Version: 1`)
  * `invalid-bad-caip2.json` (Malformed CAIP-2 network string)
  * `invalid-caip2-reference-overflow.json` (CAIP-2 network reference exceeding 32 characters)
  * `invalid-negative-amount.json` (Negative integer string)
  * `invalid-empty-accepts.json` (Empty payment options array)
  * `invalid-misplaced-carrier.json` (Conflicting/misplaced root payment carrier key)
  * `invalid-missing-kid.json` (Signing key missing required key ID)
  * `invalid-method-in-string.json` (HTTP verb embedded inside bare pointer string `"POST https://..."`)
  * `invalid-pointer-uri-template.json` (Unresolvable URI template `{agent_id}` inside pointer `url`)
  * `invalid-empty-authority.json` (Empty URI authority `https:///api/v1/search`)
  * `settlement-nonobject.json` (Non-object `extensions.settlement` rejected by schema `type` and relocation helper `ValueError`)
  * `extensions-nonobject.json` (Non-object root `extensions` rejected by schema `type` and relocation helper `ValueError`)
* **Migration Conformance Fixture Pair (`§8.2` / `§8.3`)**:
  * [`examples/migration/incumbent-legacy.json`](examples/migration/incumbent-legacy.json) (Production incumbent manifest with 76 `{url, method, description}` entries and 24 root keys including misplaced root payment carriers `payTo`, `networks`, `fee`, `access` — rejected by schema and publisher lint)
  * [`examples/migration/incumbent-v2.well-known-x402.json`](examples/migration/incumbent-v2.well-known-x402.json) (Deterministic `x402Version: 2` `self-contained` rendition — verified across all 76 entries and 19 relocated `extensions` keys)

All test cases are verified automatically via `python3 proposal/test_discovery.py` with strict RFC 3987 URI format checking enabled and 100% conformance.

---

## 8. Migration, Interoperability & Version Boundaries

### 8.1 Interoperability with PR #2 (Bare OpenAPI Pointers)
To support seamless working group consensus and interoperability with preceding exploratory drafts (such as PR #2), the schema admits manifests declaring `openapi` without `resources` (e.g. `{"x402Version": 2, "openapi": [...]}`) under its `anyOf` validation rules. While autonomous payment agents require `resources` for deterministic, zero-dependency payment resolution without secondary network hops, admitting bare `openapi` allows transitional services and documentation-only hosts to validate cleanly. Migrating hosts are encouraged to declare `resources` to unlock automated agent settlement.

### 8.2 Two Resource Entry Classes (`self-contained` vs. `pointer`), Effective `x402Version` Inheritance & Offline vs. Liveness Boundaries
Deployed `/.well-known/x402` manifests in the ecosystem (`389` pointer-only manifests and `78` all-inline manifests in the `2026-10-19` snapshot; `0` mixed) publish resource entries in two distinct shapes that make different operational promises to a client:

1. **The `pointer` Class (`pointerResource` — `{url, method?, methods?, description?, x402Version?}` or bare URI string)**:
   ```json
   {
     "url": "https://example.com/api/v1/search",
     "method": "GET",
     "description": "Search endpoint (pointer class)"
   }
   ```
   A pointer entry tells the client *that* a target URL is monetized, but omits inline settlement terms. The client must issue an HTTP request to `url` and inspect its live HTTP `402` challenge to discover `scheme`, `network`, `asset`, `amount`, and `recipient`. Because a pointer entry must be directly dereferenceable by an unparameterized reader, `url` (and bare string pointers) MUST be a strict RFC 3987 absolute `http`/`https` URI with a non-empty `reg-name` or IPv4 host (`^https?://(?:[^/?#@\s{}<>"`|\\^\[\]]+@)?[^/?#:@\s{}<>"`|\\^\[\]]+(?::[0-9]+)?(?:[/?#][^\s{}<>"`|\\^\[\]]*)?$` — bracketed IPv6 literals `[` / `]` are excluded because domain discovery is anchored on DNS `reg-name` / IPv4 authorities): strings with an empty authority or empty host (`"https:///path"`, `"https://?q"`, `"https://#frag"`, `"https://@/path"`, `"https://user@/path"`, `"https://:8080/path"`), non-numeric ports (`"https://a.example:abc/path"`, `"https://a.example:/path"`), strings that embed an HTTP verb (`"POST https://..."` — `31` manifests in the `2026-10-27` census), relative paths (`3` manifests), or unresolvable RFC 6570 URI templates (`https://.../report/{agent_id}` — `27` manifests, plus `3` combining both) are rejected by both `pattern` and `format: "uri"`. URI templates belong exclusively on `selfContainedResource.path`, where settlement terms (`accepts[]`) are already inline and matched at invocation time without a preliminary discovery fetch.
2. **The `self-contained` Class (`selfContainedResource` — `{path, accepts, description?, methods?, x402Version?}`)**:
   - **`path` Replaces `url`**: Binds the endpoint relative to the serving origin host (and MAY use RFC 6570 URI templates).
   - **Mandatory `accepts[]`**: Declares inline settlement options (`scheme`, CAIP-2 `network`, `asset`, atomic pricing bounds, and `recipient`). One manifest fetch answers every parameter required for pre-flighted payment resolution (§3) without per-route HTTP `402` probe roundtrips.
3. **Mutually Exclusive Discrimination (`if`/`then`/`else`)**: Both classes are admitted in `resources[]`, with `resourceEndpoint` branching on the presence of `path` or `accepts` and each branch enforcing `additionalProperties: false` over its disjoint key set (`path` + `accepts` vs. `url`). An entry carrying both `path` and `url` (or `url` alongside `accepts`) has no deterministic reading and is rejected by `additionalProperties` at `resources[i]`.
4. **Normative `x402Version` Inheritance, Per-Entry Precedence & Pointer Optionality**:
   - **Inheritance Is Normative**: An entry in `resources[]` that omits `x402Version` inherits the document root's `x402Version` (`effectiveVersion = entry.x402Version ?? root.x402Version`). Every `selfContainedResource` entry MUST have an effective `x402Version` of `2`—either inherited from a root `x402Version: 2` (`70/78` deployed inline manifests, requiring zero per-entry edits) or declared directly on each entry (`4/78` deployed inline manifests that carry `x402Version: 2` per entry without a root key).
   - **Pointer-Only Root Optionality (Stated on the Entries)**: For a `pointerResource` entry, a root `x402Version` (when present) is advisory; protocol version conformance for a pointer is decided at the wire by the target URL's live HTTP `402` challenge (`172/173` pointer-only manifests without a root `x402Version` whose targets answered `402` in the `2026-10-21` probe already speak `v2`). Accordingly, root `x402Version` is required unless `resources[]` is non-empty (`minItems: 1`) and every entry in `resources[]` either is a `pointerResource` or declares its own `x402Version: 2`—equivalently, root `x402Version` MUST be present whenever `resources` is absent, `resources` is empty (`[]`), or at least one entry in `resources[]` is a `selfContainedResource` that omits `x402Version`.
   - **Disagreement Precedence (`Offline Error` vs. `Runtime Wire Header Warning`)**: If both the document root and a `resources[]` entry declare `x402Version` in JSON and either differs from `2` (or they disagree with one another, as in `invalid-version-conflict.json`), offline schema validation MUST reject the document as a conformance failure (`enum` at `x402Version` or `resources[i].x402Version`). Conversely, static offline validators (CI, registry ingest) that do not dereference target URLs MUST treat root `x402Version` on a pointer manifest as advisory and MUST NOT fail a manifest on hypothetical target disagreement. When an online client or live probe dereferences a `pointerResource` target URL and its live HTTP `402` challenge version differs from a declared manifest `x402Version`, the **live `402` challenge governs the next request's wire format** and the validator SHOULD emit a diagnostic warning that explicitly names the required payment header (**`X-PAYMENT`** for `v1` vs. **`PAYMENT-SIGNATURE`** for `v2`) so operators do not ship manifests that trigger silent header-mismatch payment loops.
5. **Target HTTP Liveness, Multi-Verb Probing & Strict RFC 3987 URI Capability Verification**:
   - **Three Non-`402` Probe Populations**: Offline conformance validation is a pure function of the manifest bytes. In online ecosystem measurement (`2026-10-27` multi-verb re-probe of the `185` targets that did not return `402` to an anonymous `GET`, where `141/185` answered `402` once probed with `POST` or after separating method-prefixed strings), probes MUST distinguish three distinct populations rather than labeling every non-`402` response as unpayable: (a) **Method mismatch (`HTTP 405` / `HTTP 404` on `GET`, `HTTP 402` on `POST` — `66` + `12` targets)**, where the endpoint speaks `x402` on another verb and probes MUST try every method in `method`/`methods[]` (and retry with `POST` when omitted), surfacing `"resend with POST"` in diagnostics; (b) **Free-tier or trial allowance (`HTTP 200` to an anonymous probe)**, where the `402` challenge appears only after the allowance is exhausted or for an authenticated request, which probes SHOULD classify as *answered, payment terms unobserved*; and (c) **Unparameterized or unreachable (`HTTP 400` / `HTTP 404` / network fault across all verbs — `44` targets)**, which are genuinely unmeasured by an unparameterized probe.
   - **Normative URI Format & Runner Capability Check**: Conformance validation MUST run with strict RFC 3987 absolute HTTP(S) URI checking enabled. Because several JSON Schema libraries (such as Python `jsonschema`'s `FormatChecker()` when optional `rfc3987` is not installed, or Ajv without `ajv-formats`) silently treat `format: "uri"` as a no-op and pass arbitrary strings (`"not a uri"`), the schema pairs `format: "uri"` with an explicit host-anchored Draft-07 `pattern` (`^https?://(?:[^/?#@\s{}<>"`|\\^\[\]]+@)?[^/?#:@\s{}<>"`|\\^\[\]]+(?::[0-9]+)?(?:[/?#][^\s{}<>"`|\\^\[\]]*)?$`) and the conformance harness (`test_discovery.py`) executes a startup differential capability self-check (`assert_uri_checker_capabilities`) asserting 0 divergence between a bare `Draft7Validator(schema, format_checker=None)` and the strict format-equipped validator across valid URIs and malformed probes (`"not a uri"`, `"/relative/path"`, `"POST https://x/y"`, `"https://x/report/{agent_id}"`, `"https:///path"`, `"https://?q"`, `"https://#frag"`, `"https://@/path"`, `"https://user@/path"`, `"https://:8080/path"`, `"https://a.example:/path"`, `"https://a.example:abc/path"`, `"https://[2001:db8::1]/api"`) before evaluating any manifest.

### 8.3 Client Root-Key Tolerance vs. Publisher Relocation to `extensions`, Repair-Axis Attribution & Avoiding $O(2N)$ Route Duplication
In empirical ecosystem measurements (`783` active JSON manifests sampled on `2026-10-19` from the `1,521`-host `x402-measure` population), `770` manifests carried unrecognized root keys (`version`, `description`, `name`, `contact`, etc.) while `420` omitted `x402Version`. Because a manifest can fail on multiple rows simultaneously, those counts overlap rather than forming a partition: a v2 manifest carrying a benign root `description` field is not an unmigratable v1 document.

Accordingly, the specification separates **client acceptance**, **publisher lint strictness**, and **independent repair-axis reporting**:
1. **Client Tolerance of Benign Unknown Root Keys (`additionalProperties: true` at Root)**: Clients MUST ignore unrecognized descriptive root fields during manifest ingestion, while publisher linting (`test_discovery.py`) flags root keys outside `V2_ROOT_KEYS` (`x402Version`, `kind`, `facilitator`, `keys`, `extensions`, `resources`, `openapi`) so publishers relocate descriptive metadata (`name`, `description`, `url`, `docs`, `stats`, `register`, `agentReady`, `generated_at`, `updated`, etc.) and bespoke extension bags (`extra` $\rightarrow$ `extensions`) into the root `extensions` object.
2. **Schema Rejection of Misplaced Root Payment Carriers (`accepts`, `payTo`, `networks`, `fee`, `access`, `settlement`) & Informational Summary Validation (`extensions.settlement` / `settlementSummary`)**: Root-level payment carriers (including a root `settlement` object) create silent shadowing ambiguity against route-level terms and are explicitly forbidden at the document root across all manifests by the schema (`not.anyOf` required-key prohibitions). When upgrading a manifest to `self-contained` entries, authoritative payment carriers migrate into per-resource `resources[].accepts[]` objects (`recipient`, `network`, and `amount` / `minAmount` / `maxAmount`). Conversely, when a `pointerResource` manifest carries root `payTo`, `networks`, `fee`, or `access` solely as an informational host-level summary of terms that are already defined per-entry and governed by the live `402` challenge at runtime, the canonical one-step migration is relocating that summary object into `extensions.settlement` (which the schema validates against `definitions/settlementSummary` so non-object `extensions.settlement`, `null` / non-string `payTo` or `fee`, empty / non-array `networks`, or untyped `access` objects such as `{"x": 1}` are deterministically rejected while admitting both CAIP-2 string arrays and incumbent network/access descriptor objects as in `incumbent-legacy.json`), validating well-formed summaries with `0` errors while leaving `resources[]` byte-identical at negligible wire cost (e.g., `+82 B` raw from `37,799 B` $\rightarrow$ `37,881 B` and `+55 B` / `+0.8%` `gzip -9` from `6,612 B` $\rightarrow$ `6,667 B` on a live 81-entry `pointerResource` manifest):
   ```json
   {
     "kind": "resource-server",
     "resources": [
       { "url": "https://api.example.com/x402/gas", "method": "GET", "description": "Gas prices" },
       { "url": "https://api.example.com/x402/quote", "methods": ["GET", "POST"] }
     ],
     "extensions": {
       "settlement": {
         "payTo": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
         "networks": ["eip155:8453"],
         "fee": "0.01 USDC",
         "access": "x402"
       }
     }
   }
   ```
   Because moving `networks` (or other summary keys) under `extensions.settlement` causes local readers that only inspect the document root to fail closed rather than silently score zero networks, relocation is a two-sided change across publishers and downstream consumers: reader tooling migrating off the legacy root shape SHOULD follow both locations (`extensions.settlement.<key>` and root `<key>`, with root winning when both are present during transition, and returning `None` if `extensions` or `extensions.settlement` is not an object) for one release cycle, and automated relocation helpers (`relocate_root_settlement_carriers` in `test_discovery.py`) MUST be idempotent and abort with a single refusal class (`ValueError`) if `extensions` or `extensions.settlement` is not an object or if `extensions.settlement.<key>` already exists with a different value.
3. **Independent Repair-Axis Attribution (`describe_repair_axis` in `test_discovery.py`)**: Because the version rule (`if`/`then` + `protocolVersion`), the root misplaced-carrier rule (`not.anyOf`), and the document-role rule (`anyOf` at `domain-discovery.schema.json:85`) are orthogonal axes, conformance runners report each failing axis separately using the schema's own branch `description` strings verbatim—emitting the matched carrier keys for `not.anyOf` failures and selecting the `anyOf` branch with the fewest failing subschemas alongside its `description` (`"Resource servers declare the resources array."`, etc.) without maintaining a second hand-written vocabulary.
4. **Duplicate Route Projections (`endpoints[]`, `services[]`)**: Within `/.well-known/x402`, `resources[]` is the single normative route enumeration (§3.4). While relocating a legacy secondary route list into `extensions` is schema-valid (and counts inside the §3.4 compressed-wire budget), hosts SHOULD drop duplicated route enumerations inside `/.well-known/x402`—reducing raw payload size by `~57%` and compressed wire size by **`~33%–35%`** across independent production manifests (e.g., on the `2026-10-16T05:19:01Z` 75-route snapshot, `±0.1%` compressed across timestamp refreshes: `35,315 B` $\rightarrow$ `15,150 B` raw and `5,741 B` $\rightarrow$ `3,739 B` `gzip -9` when pretty-printed, or `28,581 B` $\rightarrow$ `12,578 B` raw and `5,545 B` $\rightarrow$ `3,620 B` `gzip -9` when compact-serialized with `separators=(',', ':')`; and independently `37,799 B` $\rightarrow$ `16,509 B` raw [`-56.3%`] and `6,612 B` $\rightarrow$ `4,461 B` `gzip -9` [`-32.5%`] on the `2026-10-27` 81-route `pointerResource` manifest)—and serve any sibling consumer projection at its own dedicated URI (such as `/.well-known/x402-service.json`).

```json
{
  "x402Version": 2,
  "resources": [ ... ],
  "extensions": {
    "name": "Acme Data Service",
    "description": "High-throughput financial intelligence",
    "stats": "https://example.com/stats",
    "register": "https://example.com/register"
  }
}
```
Compliant clients parse core payment terms from the root while preserving full access to arbitrary host-level metadata within `extensions`.
