# Domain discovery for x402 services

Draft proposal — 21 September 2026

## Proposal

Given a domain, a client needs to learn which operations it offers, what they cost, and how to pay, before making a request. Define a discovery profile for x402 services with two elements:

- A JSON document at `/.well-known/x402` that links to the service's final OpenAPI descriptions.
- An operation-level `x-x402` extension that advertises payment options, their amount ranges, and supported extensions.

`x-x402` is a static subset of the x402 v2 `PaymentRequired` object: every field it carries keeps its runtime name and meaning, so a service can describe any asset the protocol supports, and a client can check discovery against the live exchange without conversion.

Publishers may generate the final OpenAPI description directly or compose it with an OpenAPI Overlay. Both publication paths produce the same contract for clients. The publisher controls publication and may delegate generation or hosting to a provider.

## Scope

In scope:

- A per-host entry at `/.well-known/x402` that links to final OpenAPI descriptions.
- The operation-level `x-x402` annotation: payment options with advertised amount ranges, and supported extensions.
- Direct and overlay publication paths that produce the same client-facing description.
- Client interpretation rules: missing information means unspecified, annotations apply only to operations on the entry's origin, and the live exchange is authoritative.
- The HTTP transport.

Out of scope:

- **Finding domains.** Registries, crawling, search, and catalogs such as Bazaar. This profile starts from a known domain.
- **Ownership and identity.** Proving that the domain operator controls the recipient in live payment requirements, or establishing who the operator is. Discovery relies on HTTPS for document integrity and does not define signed discovery documents. These questions belong with the Identity working group.
- **Trust, reputation, and service quality.**
- **Host-wide metadata fields,** such as facilitators or signing keys. The entry admits them; their definitions are deferred to host-level discovery proposals.
- **Other transports,** such as MCP and A2A.
- **Tax** metadata, calculation, and legal determinations.
- **Changes to the runtime payment flow, SDKs, or SIWX entitlement rules.**

## Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 ([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119), [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)) when, and only when, they appear in all capitals, as shown here.

## Motivation

Clients need to discover a service's operations, understand its input and output contracts, and assess payment compatibility before making a request. OpenAPI already describes operations, schemas, and authentication. Adding x402 metadata to that description lets clients evaluate the API and its payment capabilities together.

A well-known entry gives clients a consistent starting point without duplicating the API contract. Optional amount ranges support initial selection when the amount depends on request inputs. Direct generation supports developers who configure x402 in their application; overlay composition supports providers who manage payment configuration separately.

Discovery describes advertised capabilities. The live x402 exchange remains authoritative for payment and authentication requirements.

## Design principles

1. **Publisher control.** Publication is opt-in. The publisher chooses the advertised operations and authorizes any provider that generates or hosts the description. A domain's entry advertises only that domain's operations.
2. **A small entry and a complete API description.** `/.well-known/x402` points to final OpenAPI documents. Inputs, outputs, authentication, and operation-level payment metadata remain together in OpenAPI.
3. **Reuse existing standards.** Use OpenAPI for API contracts, OpenAPI Overlay for optional composition, and existing x402 field names and meanings for payment capabilities.
4. **Equivalent publication paths.** Direct generation and overlay composition produce the same client-facing contract. A client does not need to apply overlays, and a publisher does not need a managed provider to participate.
5. **Advertise only what is known.** Payment options, amounts, and extensions are optional. Missing information means unspecified; it does not imply free access or unsupported payment capabilities.
6. **Runtime terms are authoritative.** Discovery supports selection and planning. It does not authorize payment. The live exchange determines payment and authentication requirements for the request.
7. **Authentication and payment are distinct.** Describe authentication with OpenAPI security declarations. Support paid, unpaid, and authenticated follow-up operations without treating HTTP 402 alone as proof of a payment requirement.
8. **Keep discovery public and limited in scope.** Publish service capabilities, not request-specific credentials or buyer information. Tax metadata, tax calculation, and legal determinations are outside this discovery profile.
9. **Allow capabilities to evolve.** Scheme and extension identifiers can expand without adding a separate discovery field for each mechanism. Discovery is maintained within the x402 HTTP transport specification, as described in [Versioning and protocol integration](#versioning-and-protocol-integration).

## Versioning and protocol integration

Discovery is part of the x402 protocol. The entry declares the supported protocol version through `x402Version`:

```json
{
  "x402Version": 2,
  "openapi": ["https://stabletravel.dev/openapi.json"]
}
```

The entry's `x402Version` identifies the x402 protocol version that applies to every annotation in the linked documents, initially `2`. Clients MUST NOT interpret a missing or unsupported version as `2`. Operations do not repeat the version: under [origin binding](#origin-binding), annotations are meaningful only through an entry. Discovery changes follow the protocol's specification and compatibility process. Rules for advertising multiple protocol versions in one entry remain to be defined.

Because the well-known entry and OpenAPI annotations are HTTP-specific, they would be specified in the HTTP transport specification (`specs/transports-v2/http.md`) rather than in the transport-agnostic core specification. The annotation reuses core types and identifiers (`scheme`, `network`, `asset`, `amount`, extension keys) without redefining them. Other transports, such as MCP, can define their own discovery later.

## Discovery entry

The publisher exposes `/.well-known/x402` as JSON with `Content-Type: application/json`.

| Field | Type | Definition |
| --- | --- | --- |
| `x402Version` | Integer | Required; `2`. The x402 protocol version that applies to the linked annotations. |
| `openapi` | Array of URL strings | Required and nonempty. Each URL identifies a final OpenAPI 3.1 description. |

The entry contains document locations. Operation definitions, authentication, prices, and payment options belong in the linked OpenAPI descriptions.

Clients MUST ignore entry members they do not recognize. This keeps the entry extensible without a new version for each added field.

The path follows RFC 8615 and would be registered in the IANA Well-Known URIs registry as `x402`. Like `openid-configuration` and `oauth-authorization-server`, it carries no file extension; `Content-Type` identifies the format.

### Origin binding

An entry advertises operations only for its own origin. Clients MUST apply `x-x402` annotations only to operations whose server URL has the same origin (scheme, host, and port) as the entry, and MUST ignore annotations on other operations. When an operation lists several servers, the annotation applies only to its same-origin servers. Linked OpenAPI documents MAY be hosted on another origin, for example by a provider; the entry on the publisher's origin authorizes them. Because relative server URLs resolve against the document's location, a document hosted elsewhere SHOULD use absolute server URLs. A service available on several origins publishes an entry on each.

This rule prevents one site from advertising terms for another site's operations. It does not prove who operates the origin or who controls a payment recipient; see [Scope](#scope).

### Relationship to host-level metadata

x402 should have one well-known document per host, not one per proposal. Host-wide metadata, such as facilitators or signing keys, belongs as additional members of this entry rather than in a separate document at the same path. Defining those members is out of scope here and should be aligned with other host-level discovery proposals in the working group. A client that needs only host-wide metadata reads the entry without fetching the linked OpenAPI descriptions.

## OpenAPI discovery annotation

The proposed `x-x402` extension is a member of an OpenAPI Operation Object, alongside `description`, `parameters`, and `responses`. Direct publication and overlay composition use the same field definitions.

| Field | Type | Definition |
| --- | --- | --- |
| `accepts` | Array of objects | Optional, nonempty when present. Non-exhaustive advertised payment options. |
| `accepts[].scheme` | String | Required. Scheme identifier, as in `PaymentRequirements`, such as `exact`, `upto`, or `batch-settlement`. Open string; future identifiers are allowed. |
| `accepts[].network` | String | Required. CAIP-2 network identifier, as in `PaymentRequirements`. |
| `accepts[].asset` | String | Optional; required with amount bounds. Asset identifier, as in `PaymentRequirements`: a token address or an ISO 4217 code. |
| `accepts[].minAmount` | Atomic amount string | Optional. Lower bound of the option's `amount`, in the asset's atomic units. Requires `maxAmount` and `asset`. |
| `accepts[].maxAmount` | Atomic amount string | Optional. Upper bound of the option's `amount`; at least `minAmount`. Requires `minAmount` and `asset`. |
| `extensions` | Object | Optional, nonempty when present. Keys are extension identifiers, as in `PaymentRequired.extensions`. Values are objects; see [Extensions and authentication](#extensions-and-authentication). |

An empty `x-x402` object marks an operation as using x402 without advertising terms.

### Amounts

A service advertises prices per payment option, in the terms the live exchange uses: an `asset` and a range for its `amount`, in the asset's atomic units. This covers every asset x402 supports, tokens and ISO 4217 codes alike, and needs no conversion between discovery and runtime.

`minAmount` and `maxAmount` bound the `amount` of a `PaymentRequirements` for one request with that option. Equal bounds advertise a fixed price. The meaning follows the scheme's definition of `amount`: for `upto`, the bounds describe the authorized maximum, and the settled amount can be lower. Both bounds are nonnegative integer strings, like `amount`, and `minAmount` MUST be less than or equal to `maxAmount`.

| Server configuration | Discovery option | Live `PaymentRequirements` |
| --- | --- | --- |
| `"$0.01"` | `asset` USDC on `eip155:8453`, `minAmount` and `maxAmount` `"10000"` | `"amount": "10000"` |

When bounds are present, the live `amount` for the same scheme, network, and asset SHOULD fall within them. Clients and indexers MAY flag the operation, or decline to pay, when it does not.

Clients and indexers MUST NOT interpret omitted bounds as zero, or `maxAmount` as a guaranteed spending cap. Bounds describe advertised prices across supported inputs, not request-specific quotes. Charging conditions use the existing OpenAPI operation `description`, consistent with runtime `resource.description`.

Comparing operations priced in different assets is left to clients and indexers. They convert atomic amounts using each asset's decimals, and a peg or exchange rate where needed, as x402 clients already do to enforce spending limits on known stablecoins.

### Payment options

`accepts` advertises a non-exhaustive set of payment options. Each field keeps its x402 v2 `PaymentRequirements` meaning. `scheme` is an open string: `exact`, `upto`, `batch-settlement`, and future schemes use the same field. Clients need an implementation of the selected scheme; an unknown identifier MUST NOT be treated as `exact`.

Discovery options are summaries, not runtime `PaymentRequirements` objects. Clients MUST obtain fresh requirements before payment. The live exchange supplies the exact `amount`, the recipient `payTo`, `maxTimeoutSeconds`, and mechanism-specific `extra` fields. Discovery leaves them out because they are request-bound or only needed to pay: the Solana option in the StableStudio example below carries a recent blockhash in `extra`, for instance.

### Extensions and authentication

`extensions` has the shape of runtime `PaymentRequired.extensions`: an object keyed by extension identifier. A key advertises operation-level support for that extension. Its value is an object for static information that the extension defines; publishers use `{}` when it defines none. Runtime extension data, and whether an extension applies to a given request, come from the live exchange. Omission means support is unspecified.

For example, `"extensions": {"sign-in-with-x": {}}` advertises SIWX support. Authentication requirements remain in OpenAPI `security` and `components.securitySchemes`. The operation description states conditions for access, including access to previously purchased resources. Support alone does not require a signature on every request or establish entitlement.

An authentication-only operation may advertise `extensions` without `accepts`. Presence of `x-x402` alone does not establish a payment requirement. Clients MUST NOT assume that an unknown extension can be ignored when the live flow requires it.

Static discovery MUST NOT contain request-bound nonces, blockhashes, signatures, or authorizations.

## Publication

Publishers derive discovery annotations from the service's payment configuration and validate them against the [annotation schema](x-x402.schema.json). They also validate the OpenAPI description and amount-bound ordering.

Two publication paths are supported:

1. **Direct publication.** The application's OpenAPI generator or build step adds `x-x402` to the relevant operations.
2. **Overlay composition.** A provider supplies an OpenAPI Overlay with the annotations. The publisher applies the overlay, validates the result, and publishes the final description.

Clients consume the final description in both cases. They do not need to fetch or apply overlays. Publishers validate overlay targets, conflicts, and duplicate payment options before publication. Overlay updates merge objects and append arrays.

The OpenAPI description documents the x402 HTTP 402 response and its `PAYMENT-REQUIRED` header, which carries a base64-encoded `PaymentRequired` object. It also includes unpaid and authenticated follow-up operations needed to use the advertised service.

Publication is opt-in. Publishers regenerate descriptions when routes, payment configuration, or advertised amounts change. Retiring operations use OpenAPI `deprecated: true`; withdrawn operations are removed from the next publication. HTTP responses remain authoritative about current availability. Cached discovery does not guarantee that an endpoint or price remains available.

Publishers MAY provide the standard HTTP `Last-Modified` response header for the discovery entry and each linked OpenAPI document to help clients check for updates.

## Examples

The following examples apply the proposed profile to selected operations from StableTravel and StableStudio. They illustrate publication under this proposal, not deployment of the profile by those services.

### Fixed price data service

StableTravel's `GET /api/seats-aero/routes` returns airline origin/destination pairs for a mileage program. The required `source` query parameter selects the program, for example `united`. Response records include `OriginAirport`, `DestinationAirport`, `Distance`, and `NumDaysOut`.

The discovery entry is:

```json
{
  "x402Version": 2,
  "openapi": ["https://stabletravel.dev/openapi.json"]
}
```

The following complete OpenAPI Overlay applies to the service's base OpenAPI description. It targets one operation and adds one observed Base payment option, priced at the documented USD 0.01 as a fixed `10000` atomic units of USDC (6 decimals), and the payment challenge header. The base document supplies the parameters and response schemas.

```json
{
  "overlay": "1.1.0",
  "info": {
    "title": "Proposed StableTravel discovery annotations",
    "version": "2026-09-21"
  },
  "actions": [
    {
      "target": "$['paths']['/api/seats-aero/routes']['get']",
      "update": {
        "description": "List airline flight route pairs covered by a Seats.aero mileage program source. These are origin/destination airport pairs, not API routes. Charged per request.",
        "x-x402": {
          "accepts": [
            {
              "scheme": "exact",
              "network": "eip155:8453",
              "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
              "minAmount": "10000",
              "maxAmount": "10000"
            }
          ]
        },
        "responses": {
          "402": {
            "headers": {
              "PAYMENT-REQUIRED": {
                "description": "Base64-encoded x402 v2 PaymentRequired object. Obtain fresh request-specific terms before payment.",
                "schema": {
                  "type": "string"
                }
              }
            }
          }
        }
      }
    }
  ]
}
```

Applying this overlay preserves the operation's input and success-response contracts. The publisher serves the resulting OpenAPI document at the URL in the discovery entry. Direct generation adds the same `x-x402`, description, and header definitions to the operation without an overlay.

### Final combined OpenAPI document

The result below is the complete OpenAPI document for the single StableTravel endpoint. It includes the base operation's required `source` parameter and full response schema, together with the overlay's description, payment challenge header, and `x-x402` annotation. This is the document referenced by `/.well-known/x402` and read by clients.

<!-- final-stabletravel:start -->
```json
{
  "openapi": "3.1.0",
  "servers": [{"url": "https://stabletravel.dev"}],
  "info": {"title": "StableTravel", "version": "1.0.0"},
  "paths": {
    "/api/seats-aero/routes": {
      "get": {
        "operationId": "seats-aero_routes",
        "summary": "List airline flight route pairs covered by a Seats.aero mileage program source. These are origin/destination airport pairs, not API routes.",
        "tags": ["Seats Aero"],
        "parameters": [
          {
            "in": "query",
            "name": "source",
            "schema": {
              "type": "string",
              "minLength": 1,
              "description": "Seats.aero mileage program source, such as united or aeroplan"
            },
            "required": true,
            "description": "Seats.aero mileage program source, such as united or aeroplan"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "ID": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "Source": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "OriginAirport": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "DestinationAirport": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "OriginRegion": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "DestinationRegion": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      "Distance": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                      "NumDaysOut": {"anyOf": [{"type": "number"}, {"type": "null"}]}
                    },
                    "additionalProperties": {}
                  }
                }
              }
            }
          },
          "402": {
            "description": "Payment Required",
            "headers": {
              "PAYMENT-REQUIRED": {
                "description": "Base64-encoded x402 v2 PaymentRequired object. Obtain fresh request-specific terms before payment.",
                "schema": {"type": "string"}
              }
            }
          }
        },
        "description": "List airline flight route pairs covered by a Seats.aero mileage program source. These are origin/destination airport pairs, not API routes. Charged per request.",
        "x-x402": {
          "accepts": [
            {
              "scheme": "exact",
              "network": "eip155:8453",
              "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
              "minAmount": "10000",
              "maxAmount": "10000"
            }
          ]
        }
      }
    }
  }
}
```
<!-- final-stabletravel:end -->

The [base OpenAPI](examples/stabletravel.source.openapi.json), [overlay](examples/stabletravel.overlay.json), and [final combined OpenAPI](examples/stabletravel.final.openapi.json) are included in the repository. The base capture's source-specific payment metadata is removed before composition, as described in the example documentation.

### Variable price asynchronous service

StableStudio's `POST /api/generate/nano-banana-pro/generate` accepts a prompt, aspect ratio, and image size. It returns a job identifier and polling URL. Its annotation advertises the two payment options observed in a live challenge, each with the documented USD 0–10.00 range expressed in USDC atomic units (6 decimals on both networks):

```json
"x-x402": {
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "minAmount": "0",
      "maxAmount": "10000000"
    },
    {
      "scheme": "exact",
      "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
      "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "minAmount": "0",
      "maxAmount": "10000000"
    }
  ]
}
```

The live challenge for a request with default settings asked for `130000` (USD 0.13) on both networks, within the advertised range. Its Solana option also carried a recent blockhash in `extra`, which discovery leaves out. The lower bound of `0` is copied from the service's published range; it does not declare free access. The operation `description` states that the price is dynamic within the range.

The description also includes `GET /api/jobs/{jobId}`. It declares SIWX in `security` and advertises `"extensions": {"sign-in-with-x": {}}` without payment options. The generate response uses an OpenAPI link to pass `jobId` to that operation, so the asynchronous follow-up is machine-readable without new fields. The authentication response's use of HTTP 402 does not itself establish a payment requirement.

### Additional annotation variations

The following operation fragments illustrate distinct cases permitted by the proposed contract. They are independent alternatives, not cumulative overlay updates, and do not assert additional capabilities for the Stable services. The fixed-price example above covers a fixed amount; the asynchronous example covers amount ranges on two networks and an authentication-only follow-up.

#### Terms omitted

An operation can mark x402 use without publishing payment options or amounts. Clients obtain terms at runtime; this does not declare free access.

```json
{
  "x-x402": {}
}
```

#### Multiple payment schemes

Separate options advertise each supported scheme/network combination. The operation can offer `exact`, `upto`, and `batch-settlement` without introducing separate fields for those schemes. Future identifiers use the same field.

```json
{
  "x-x402": {
    "accepts": [
      {
        "scheme": "exact",
        "network": "eip155:8453"
      },
      {
        "scheme": "upto",
        "network": "eip155:8453"
      },
      {
        "scheme": "batch-settlement",
        "network": "eip155:8453"
      }
    ]
  }
}
```

Options can also span networks, each with its own asset and amounts. Each uses the canonical CAIP-2 identifier; for Algorand MainNet that is the first 32 characters of the genesis hash, not `mainnet`:

```json
{
  "x-x402": {
    "accepts": [
      {
        "scheme": "exact",
        "network": "eip155:8453",
        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "minAmount": "10000",
        "maxAmount": "10000"
      },
      {
        "scheme": "exact",
        "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
        "asset": "31566704",
        "minAmount": "10000",
        "maxAmount": "10000"
      }
    ]
  }
}
```

#### Payment with SIWX support

An operation can advertise both payment and SIWX. Its description states when a previously entitled wallet can authenticate instead of paying again. Required authentication and alternative access conditions remain part of the OpenAPI contract.

```json
{
  "x-x402": {
    "accepts": [
      {
        "scheme": "exact",
        "network": "eip155:8453"
      }
    ],
    "extensions": {
      "sign-in-with-x": {}
    }
  }
}
```

#### Authentication without payment

An authentication-only operation advertises SIWX without payment options, as the StableStudio polling operation does. Its OpenAPI Operation Object references the corresponding security scheme:

```json
{
  "description": "Authenticate with a wallet signature. No payment is required.",
  "security": [{"siwx": []}],
  "x-x402": {
    "extensions": {"sign-in-with-x": {}}
  }
}
```

The referenced scheme is defined in the same OpenAPI document:

```json
{
  "components": {
    "securitySchemes": {
      "siwx": {
        "type": "apiKey",
        "in": "header",
        "name": "SIGN-IN-WITH-X",
        "description": "Base64-encoded SIWX proof obtained by signing a fresh server challenge."
      }
    }
  }
}
```

## References

- [x402 v2 specification](https://github.com/x402-foundation/x402/blob/main/specs/x402-specification-v2.md)
- [OpenAPI specification extensions](https://spec.openapis.org/oas/v3.1.1.html#specification-extensions)
- [OpenAPI Overlay specification](https://spec.openapis.org/overlay/v1.1.0.html)
- [Batch settlement](https://docs.x402.org/schemes/batch-settlement)
- [Sign-In-With-X](https://docs.x402.org/extensions/sign-in-with-x)
- [StableTravel OpenAPI](https://stabletravel.dev/openapi.json)
- [StableStudio OpenAPI](https://stablestudio.dev/openapi.json)

Source captures, provenance, and reproduction instructions are in the [example documentation](examples/README.md).
