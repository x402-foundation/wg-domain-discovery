# Example sources and verification

These examples adapt selected operations from StableTravel and StableStudio to the proposed discovery profile. They do not assert merchant endorsement or deployment of this profile.

The fixtures use the author-preferred Option A: discovery within the x402 protocol, with `x402Version: 2` in the entry and matching operation annotations, without a separate `discoveryVersion`. Option B remains documented in the proposal.

## Variations

| Case | Example |
| --- | --- |
| Fixed price, exact payment, public recipient | `stabletravel.overlay.json` — complete overlay for one real data endpoint |
| Price range, payment options omitted, asynchronous follow-up | Generated StableStudio document from the captured operations |
| Price and payment options omitted | `annotation-variants.json`: `price-omitted` |
| Multiple payment schemes | `annotation-variants.json`: `payment-schemes` |
| Payment with SIWX support | `annotation-variants.json`: `siwx-with-payment` |
| Authentication only | `annotation-variants.json`: `siwx-authentication-only`; proposal includes its security declaration |
| Scheme-defined recipient role | `annotation-variants.json`: `role-recipient` |
| Stealth recipient signal | `annotation-variants.json`: `stealth-recipient` |

Annotation variants are independent contract examples, not statements about Stable service support. Role and stealth examples contain explicit mechanism placeholders. They are not payment instructions or deployable payment configurations. The full single-endpoint overlay and the variations are also shown inline in the proposal.

## Generate the publication artifacts

From the repository root:

```sh
python3 proposals/openapi-publication/check_examples.py --write
```

The generated final documents are committed as [stabletravel.final.openapi.json](stabletravel.final.openapi.json) and [stablestudio.final.openapi.json](stablestudio.final.openapi.json). `--write` refreshes those files. The checker verifies that they match the generated output and that the complete StableTravel document embedded in the proposal matches as well.

Publication outputs are also written under `proposals/openapi-publication/build/`, with one `openapi.json` and one `.well-known/x402.json` entry per service. The command is offline and does not publish files or make payments.

The check verifies captured operation hashes, local references, direct/overlay equivalence, preservation of input/output contracts, optional prices and ranges, authentication, entry URLs, and rejection of missing overlay targets. It is not a general OpenAPI, JSON Schema, or Overlay validator. Validate annotations separately against `../x-x402.schema.json`.

## Source evidence

Sources were captured on 21 September 2026. `evidence.json` records source and operation hashes. Files ending in `.source.openapi.json` retain the selected source operations and their schemas.

StableTravel uses `GET /api/seats-aero/routes?source=united`. Its documentation supplies the fixed USD price. An unsigned request returned HTTP 402; `stabletravel.challenge-excerpt.json` records one observed Base payment option and a Bazaar output example. No payment was made. The live challenge also advertised Solana, so the selected option is not exhaustive. The output example is server-supplied metadata, not a purchased response.

StableStudio uses `POST /api/generate/nano-banana-pro/generate` and `GET /api/jobs/{jobId}`. The source supplies the USD price range and polling security declaration. The build adds the required string `jobId` path parameter omitted by the source. It retains the source response schemas, including the unconstrained `result` field.

## Source conversion

The build removes the source-specific `x-payment-info` block before adding the proposed discovery annotation. Published example outputs contain only the proposed x402 discovery fields. The omission of source MPP metadata scopes the example to x402; it does not imply a change in the real service's payment support.

Source normalization happens before overlay composition. The example composer supports only the exact object-member targets used in the fixture. It rejects missing targets as a build safeguard; standard Overlay processing treats a target with no matches as a no-op. Production implementations need standard tooling and checks against deployed configuration.

Use your own routes, document locations, and payment configuration when adapting the examples. The captured StableTravel recipient belongs to that example service.
