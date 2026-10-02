# Example sources and verification

These examples adapt selected operations from StableTravel and StableStudio to the proposed discovery profile. They do not assert merchant endorsement or deployment of this profile.

The fixtures declare `x402Version: 2` once, in the entry. Operation annotations do not repeat it.

## Variations

| Case | Example |
| --- | --- |
| Fixed amount, exact payment | `stabletravel.overlay.json` — complete overlay for one real data endpoint |
| Amount ranges on two networks, asynchronous follow-up with an OpenAPI link | Generated StableStudio document from the captured operations and challenge |
| Terms omitted | `annotation-variants.json`: `terms-omitted` |
| Multiple payment schemes | `annotation-variants.json`: `payment-schemes` |
| Multiple networks | `annotation-variants.json`: `multiple-networks` |
| Payment with SIWX support | `annotation-variants.json`: `siwx-with-payment` |
| Authentication only | StableStudio `GET /api/jobs/{jobId}`; `annotation-variants.json`: `siwx-authentication-only` |

Annotation variants are independent contract examples, not statements about Stable service support. They are not payment instructions or deployable payment configurations. The full single-endpoint overlay and the variations are also shown inline in the proposal.

## Generate the publication artifacts

From the repository root:

```sh
python3 proposals/openapi-publication/check_examples.py --write
```

The generated final documents are committed as [stabletravel.final.openapi.json](stabletravel.final.openapi.json) and [stablestudio.final.openapi.json](stablestudio.final.openapi.json). `--write` refreshes those files. The checker verifies that they match the generated output and that the complete StableTravel document embedded in the proposal matches as well.

Publication outputs are also written under `proposals/openapi-publication/build/`, with one `openapi.json` and one `.well-known/x402` entry per service. The command is offline and does not publish files or make payments.

The check verifies captured operation hashes, local references, direct/overlay equivalence, preservation of input/output contracts, agreement between documented prices and live amounts, optional amount ranges, authentication, entry URLs, and rejection of missing overlay targets. It is not a general OpenAPI, JSON Schema, or Overlay validator. Validate annotations separately against `../x-x402.schema.json`.

## Source evidence

Sources were captured on 21 September 2026. `evidence.json` records source and operation hashes. Files ending in `.source.openapi.json` retain the selected source operations and their schemas.

StableTravel uses `GET /api/seats-aero/routes?source=united`. Its documentation supplies the fixed price of USD `0.010000`. The checker confirms that it equals the live `amount` of `10000` USDC atomic units (6 decimals), which the annotation advertises as equal bounds. The build appends "Charged per request." to the captured runtime description. An unsigned request returned HTTP 402; `stabletravel.challenge-excerpt.json` records one observed Base payment option and a Bazaar output example. No payment was made. The live challenge also advertised Solana, so the selected option is not exhaustive. The output example is server-supplied metadata, not a purchased response.

StableStudio uses `POST /api/generate/nano-banana-pro/generate` and `GET /api/jobs/{jobId}`. The source supplies the USD `0`–`10.00` price range and polling security declaration. An unsigned request with default settings, captured on 1 October 2026, returned HTTP 402 with Base and Solana USDC options at `130000` each; `stablestudio.challenge-excerpt.json` records it without the Bazaar extension. No payment was made. The annotation advertises both options with the documented range in USDC atomic units, and the checker confirms the live amounts fall within it. The build adds the required string `jobId` path parameter omitted by the source, an operation `description` for the generate operation, an OpenAPI link from the generate response to the polling operation, a description for the `siwx` security scheme, and an authentication-only `x-x402` annotation on the polling operation, whose SIWX requirement the source documents. It retains the source response schemas, including the unconstrained `result` field.

## Source conversion

The build removes the source-specific `x-payment-info` block before adding the proposed discovery annotation. Published example outputs contain only the proposed x402 discovery fields. The omission of source MPP metadata scopes the example to x402; it does not imply a change in the real service's payment support.

Source normalization happens before overlay composition. The example composer supports only the exact object-member targets used in the fixture. It rejects missing targets as a build safeguard; standard Overlay processing treats a target with no matches as a no-op. Production implementations need standard tooling and checks against deployed configuration.

Use your own routes, document locations, and payment configuration when adapting the examples. The captured challenges contain recipients that belong to those example services; discovery does not advertise recipients.
