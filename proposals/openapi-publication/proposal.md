# Domain discovery for x402 services

Draft proposal — 21 September 2026

## Proposal

Define a domain discovery profile for x402 services with two elements:

- A JSON document at `/.well-known/x402.json` that links to the service's final OpenAPI descriptions.
- An operation-level `x-x402` extension that advertises the x402 version, optional prices, payment options, and extension capabilities.

Publishers may generate the final OpenAPI description directly or compose it with an OpenAPI Overlay. Both publication paths produce the same contract for clients. The publisher controls publication and may delegate generation or hosting to a provider.

## Motivation

Clients need to discover a service's operations, understand its input and output contracts, and assess payment compatibility before making a request. OpenAPI already describes operations, schemas, and authentication. Adding x402 metadata to that description lets clients evaluate the API and its payment capabilities together.

A well-known entry gives clients a consistent starting point without duplicating the API contract. Optional price ranges support initial selection when the amount depends on request inputs. Direct generation supports developers who configure x402 in their application; overlay composition supports providers who manage payment configuration separately.

Discovery describes advertised capabilities. The live x402 exchange remains authoritative for payment and authentication requirements.

## Design principles

1. **Publisher control.** Publication is opt-in. The publisher chooses the advertised operations and authorizes any provider that generates or hosts the description.
2. **A small entry and a complete API description.** `/.well-known/x402.json` points to final OpenAPI documents. Inputs, outputs, authentication, and operation-level payment metadata remain together in OpenAPI.
3. **Reuse existing standards.** Use OpenAPI for API contracts, OpenAPI Overlay for optional composition, and existing x402 identifiers for payment capabilities.
4. **Equivalent publication paths.** Direct generation and overlay composition produce the same client-facing contract. A client does not need to apply overlays, and a publisher does not need a managed provider to participate.
5. **Advertise only what is known.** Prices, payment options, and recipients are optional. Missing information means unspecified; it does not imply free access or unsupported payment capabilities.
6. **Runtime terms are authoritative.** Discovery supports selection and planning. It does not authorize payment. The live exchange determines payment and authentication requirements for the request.
7. **Authentication and payment are distinct.** Describe authentication with OpenAPI security declarations. Support paid, unpaid, and authenticated follow-up operations without treating HTTP 402 alone as proof of a payment requirement.
8. **Keep discovery public and limited in scope.** Publish service capabilities, not request-specific credentials or buyer information. Tax metadata, tax calculation, and legal determinations are outside this discovery profile.
9. **Allow capabilities to evolve.** Scheme and extension identifiers can expand without adding a separate discovery field for each mechanism. Prefer maintaining discovery within the x402 protocol specification, as described in Option A.

## Protocol integration and versioning

Two approaches are proposed for consideration. Both use `/.well-known/x402.json` and the same OpenAPI annotations.

### Option A Discovery within the x402 protocol — preferred

Define the entry format and OpenAPI annotations as part of the x402 protocol specification. The entry declares the supported payment protocol through `x402Version`, without a separate `discoveryVersion` field:

```json
{
  "x402Version": 2,
  "openapi": ["https://stabletravel.dev/openapi.json"]
}
```

The entry's `x402Version` identifies the supported x402 payment protocol, initially `2`. Each advertised operation's `x-x402.x402Version` MUST match that version. Clients MUST NOT interpret a missing or unsupported entry version as `2`. Discovery changes follow the protocol's specification and compatibility process; `x402Version` is not an independent discovery version. Rules for future incompatible discovery changes and for advertising multiple protocol versions in one entry remain to be defined.

### Option B Separate discovery version

Define discovery as a separately versioned profile. The entry requires `discoveryVersion`, which versions the entry format and discovery annotations independently of the payment protocol:

```json
{
  "discoveryVersion": "1",
  "openapi": ["https://stabletravel.dev/openapi.json"]
}
```

This allows the discovery format to evolve without changing the payment protocol version. Clients must support the advertised discovery version; they must not interpret a missing or unsupported value as `"1"`. The tradeoff is an additional version and compatibility policy for implementers to manage.

### Author preference

I prefer Option A. Discovery should be part of the x402 protocol, with its entry format and OpenAPI annotations maintained in the same specification process. I would not introduce `discoveryVersion`. The entry should declare the supported `x402Version`, with matching versions on operations, so developers implement one coherent protocol specification.

This is the author's preference, not an adopted working-group decision. The examples and executable fixtures below use Option A to make that approach concrete; Option B remains an alternative.

## Discovery entry

The publisher exposes `/.well-known/x402.json` as JSON with `Content-Type: application/json`.

| Field | Type | Definition |
| --- | --- | --- |
| `openapi` | Array of URL strings | Required and nonempty under both options. Each URL identifies a final OpenAPI 3.1 description. |
| `discoveryVersion` | String | Required as `"1"` under Option B; absent under Option A. |
| `x402Version` | Integer | Required as `2` under Option A; identifies the supported x402 protocol version. Not an entry field under Option B. |

The entry contains document locations. Operation definitions, authentication, prices, and payment options belong in the linked OpenAPI descriptions.

## OpenAPI discovery annotation

The proposed `x-x402` extension is a member of an OpenAPI Operation Object, alongside `description`, `parameters`, and `responses`. Direct publication and overlay composition use the same field definitions.

| Field | Type | Definition |
| --- | --- | --- |
| `x402Version` | Integer | Required; `2`. Advertises x402 v2 support. |
| `price` | Object | Optional advertised price range for the operation. Omit when unknown or unsuitable. |
| `price.currency` | String | Required if price is present. ISO 4217 currency code, such as `USD`. |
| `price.min` | Decimal string | Required if price is present. Nonnegative advertised lower bound in major currency units. |
| `price.max` | Decimal string | Required if price is present. Nonnegative advertised upper bound; must be at least `min`. |
| `accepts` | Array of objects | Optional, nonempty when present. Non-exhaustive advertised x402 payment options. |
| `accepts[].scheme` | String | Required in each advertised option. Native scheme identifier, such as `exact`, `upto`, or `batch-settlement`. Open string; future identifiers are allowed. |
| `accepts[].network` | String | Required in each advertised option. Native CAIP-2 network identifier. |
| `accepts[].asset` | String | Optional. Native asset identifier, if known in advance. |
| `accepts[].payTo` | String | Optional. Native recipient identifier, only if suitable for public discovery. Requires `payToType`. |
| `accepts[].payToType` | String | Optional payout declaration: `address`, `role`, or `stealth`. `address` and `role` require `payTo`; `stealth` omits it. |
| `extensions` | Array of strings | Optional, nonempty list of unique extension identifiers supported for this operation, such as `sign-in-with-x`. |

### Prices

Price information is optional, including fixed prices. If `price` is present, `currency`, `min`, and `max` are required. Both bounds are nonnegative decimal strings in major units of the stated ISO 4217 currency, and `min` MUST be less than or equal to `max`. Equal bounds indicate fixed advertised pricing.

A range describes advertised prices across supported inputs. Clients MUST NOT interpret an omitted price as zero or an advertised maximum as a guaranteed spending cap. The price is not a request-specific quote or an asset exchange rate. Charging conditions use the existing OpenAPI operation `description`, consistent with runtime `resource.description`.

### Payment options

`accepts` advertises a non-exhaustive set of scheme/network combinations. The identifiers `scheme`, `network`, `asset`, and `payTo` retain their x402 v2 meanings. `scheme` is an open string: `exact`, `upto`, `batch-settlement`, and future schemes use the same field. Clients need an implementation of the selected scheme; an unknown identifier MUST NOT be treated as `exact`.

Discovery options are summaries, not runtime `PaymentRequirements` objects. Clients MUST obtain fresh requirements before payment. The live exchange supplies the atomic asset `amount`, `maxTimeoutSeconds`, and mechanism-specific `extra` fields. Those fields are not part of this discovery annotation. A price range does not imply a particular payment scheme.

Optional `payTo` identifies an advertised recipient. It does not prove ownership. The proposed `payToType` distinguishes a public wallet `address`, a scheme-defined recipient `role`, and `stealth` recipient handling. `address` and `role` require `payTo`; `stealth` MUST omit it and signals that clients cannot assume a reusable public recipient. The payment mechanism supplies the runtime recipient. If payout information is unknown, both fields are omitted.

### Extensions and authentication

The optional `extensions` list contains unique identifiers matching the keys used in runtime x402 extension objects. It advertises operation-level support; it is not a runtime extension payload. Omission means support is unspecified. Applicability to a payment option or request, and any required extension data, are determined by the live exchange.

For example, `"extensions": ["sign-in-with-x"]` advertises SIWX support. Authentication requirements remain in OpenAPI `security` and `components.securitySchemes`. The operation description states conditions for access, including access to previously purchased resources. Support alone does not require a signature on every request or establish entitlement.

An authentication-only operation may advertise `x402Version` and `extensions` while omitting `price` and `accepts`. Presence of `x-x402` alone does not establish a payment requirement. Clients MUST NOT assume that an unknown extension can be ignored when the live flow requires it.

Static discovery MUST NOT contain request-bound nonces, blockhashes, signatures, or authorizations.

## Publication

Publishers derive discovery annotations from the service's payment configuration and validate them against the [annotation schema](x-x402.schema.json). They also validate the OpenAPI description, currency identifiers, and price-bound ordering.

Two publication paths are supported:

1. **Direct publication.** The application's OpenAPI generator or build step adds `x-x402` to the relevant operations.
2. **Overlay composition.** A provider supplies an OpenAPI Overlay with the annotations. The publisher applies the overlay, validates the result, and publishes the final description.

Clients consume the final description in both cases. They do not need to fetch or apply overlays. Publishers validate overlay targets, conflicts, and duplicate payment options before publication. Overlay updates merge objects and append arrays.

The OpenAPI description documents the x402 HTTP 402 response and its `PAYMENT-REQUIRED` header, which carries a base64-encoded `PaymentRequired` object. It also includes unpaid and authenticated follow-up operations needed to use the advertised service.

Publication is opt-in. Publishers regenerate descriptions when routes, payment configuration, or advertised prices change. Retiring operations use OpenAPI `deprecated: true`; withdrawn operations are removed from the next publication. HTTP responses remain authoritative about current availability. Cached discovery does not guarantee that an endpoint or price remains available.

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

The following complete OpenAPI Overlay applies to the service's base OpenAPI description. It targets one operation and adds the documented USD 0.01 price, one observed Base payment option, and the payment challenge header. The base document supplies the parameters and response schemas.

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
        "description": "List airline flight route pairs covered by a Seats.aero mileage program source. These are origin/destination airport pairs, not API routes.",
        "x-x402": {
          "x402Version": 2,
          "price": {
            "currency": "USD",
            "min": "0.010000",
            "max": "0.010000"
          },
          "accepts": [
            {
              "scheme": "exact",
              "network": "eip155:8453",
              "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
              "payTo": "0xDd257723b86B4947483905cdAcBbBC70fACF2ec0",
              "payToType": "address"
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

The result below is the complete OpenAPI document for the single StableTravel endpoint. It includes the base operation's required `source` parameter and full response schema, together with the overlay's description, payment challenge header, and `x-x402` annotation. This is the document referenced by `/.well-known/x402.json` and read by clients.

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
        "description": "List airline flight route pairs covered by a Seats.aero mileage program source. These are origin/destination airport pairs, not API routes.",
        "x-x402": {
          "x402Version": 2,
          "price": {"currency": "USD", "min": "0.010000", "max": "0.010000"},
          "accepts": [
            {
              "scheme": "exact",
              "network": "eip155:8453",
              "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
              "payTo": "0xDd257723b86B4947483905cdAcBbBC70fACF2ec0",
              "payToType": "address"
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

StableStudio's `POST /api/generate/nano-banana-pro/generate` accepts a prompt, aspect ratio, and image size. It returns a job identifier and polling URL. Its documented price range is represented as:

```json
"x-x402": {
  "x402Version": 2,
  "price": {
    "currency": "USD",
    "min": "0",
    "max": "10.00"
  }
}
```

Payment options are omitted when no reusable option is established. The live challenge supplies terms for the selected prompt and image settings.

The description also includes `GET /api/jobs/{jobId}` with its SIWX security declaration. The authentication response's use of HTTP 402 does not itself establish a payment requirement.

### Additional annotation variations

The following operation fragments illustrate distinct cases permitted by the proposed contract. They are independent alternatives, not cumulative overlay updates, and do not assert additional capabilities for the Stable services. The fixed-price example above also covers a public address; the asynchronous example covers a price range and omitted payment options.

#### Price and payment options omitted

An operation can advertise protocol support without publishing a price or reusable payment options. Clients obtain terms at runtime; this does not declare free access.

```json
{
  "x-x402": {
    "x402Version": 2
  }
}
```

#### Multiple payment schemes

Separate options advertise each supported scheme/network combination. The operation can offer `exact`, `upto`, and `batch-settlement` without introducing separate fields for those schemes. Future identifiers use the same field.

```json
{
  "x-x402": {
    "x402Version": 2,
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

#### Payment with SIWX support

An operation can advertise both payment and SIWX. Its description states when a previously entitled wallet can authenticate instead of paying again. Required authentication and alternative access conditions remain part of the OpenAPI contract.

```json
{
  "x-x402": {
    "x402Version": 2,
    "accepts": [
      {
        "scheme": "exact",
        "network": "eip155:8453"
      }
    ],
    "extensions": [
      "sign-in-with-x"
    ]
  }
}
```

#### Authentication without payment

An authentication-only operation advertises SIWX without price or payment options. Its OpenAPI Operation Object references the corresponding security scheme:

```json
{
  "description": "Authenticate with a wallet signature. No payment is required.",
  "security": [{"siwx": []}],
  "x-x402": {
    "x402Version": 2,
    "extensions": ["sign-in-with-x"]
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

#### Recipient variants

The complete StableTravel overlay uses `payToType: "address"` with a public recipient. The following fragments illustrate the other proposed discovery declarations. `mechanism-defined-scheme` and `mechanism-defined-role` are placeholders: a publisher must substitute identifiers from a mechanism that actually supports the declared behavior. These examples do not establish support in an existing scheme.

A role recipient includes the scheme-defined role in `payTo`:

```json
{
  "x-x402": {
    "x402Version": 2,
    "accepts": [
      {
        "scheme": "mechanism-defined-scheme",
        "network": "eip155:8453",
        "payTo": "mechanism-defined-role",
        "payToType": "role"
      }
    ]
  }
}
```

A stealth declaration omits `payTo`; the applicable mechanism supplies the recipient at runtime:

```json
{
  "x-x402": {
    "x402Version": 2,
    "accepts": [
      {
        "scheme": "mechanism-defined-scheme",
        "network": "eip155:8453",
        "payToType": "stealth"
      }
    ]
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
