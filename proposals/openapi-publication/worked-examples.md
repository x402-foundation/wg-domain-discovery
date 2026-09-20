# Worked examples and technical evidence

These examples support the [publication proposal](proposal.md). Captured public documentation is evidence, not proof of runtime behavior or merchant approval.

## StableTravel with direct publication

StableTravel is a useful direct-publication example because its existing OpenAPI document already contains operation schemas and payment metadata. A developer could produce that final artifact from application routes and SDK payment configuration, then publish the small entry document. There is no overlay in this path.

The selected example contains three operations: Google Flights search, booking-link lookup, and Seats.aero trip details. The public guide describes flight data and external booking links, not ticket issuance, hotels, activities, or transfers. [T1][T2]

An illustrative one-way request uses these documented parameters. It was not sent:

```text
GET /api/google-flights/search
departure_id=FCO
arrival_id=LHR
outbound_date=2026-11-12
type=2
```

The source advertises the search price in display currency:

```json
"price": {
  "mode": "fixed",
  "currency": "USD",
  "amount": "0.020000"
}
```

This is a field inside the service’s existing x-payment-info object. It is not x402 PaymentRequirements.amount. Do not turn it into an atomic token amount without knowing the actual asset and unit rules. The example preserves it unchanged and adds only the proposed payment summary.

The source schema uses `/api/seats-aero/trips/id`, while its usage guide describes `/api/seats-aero/trips/{id}`. Our example proposes the latter and declares the required string path parameter. That correction needs operator confirmation before deployment. A structurally valid document can still describe the wrong route.

**What this tests:** the well-known proposal works with a merchant-maintained final document; no facilitator-generated schema or merchant-authored overlay is necessary. It also shows why publication checks must compare route configuration and documentation, not just parse JSON.

Files: `examples/stabletravel/well-known.json`, `final.openapi.json`, and `changes.json`.



## StableStudio with paid creation and authenticated polling

The selected example describes Nano Banana Pro generation and job-status polling. Creation is paid and asynchronous. The guide says polling uses SIGN-IN-WITH-X authentication with no new payment. Its OpenAPI describes an authentication-required 402 response on the polling route. [S1][S2]

The proposed polling operation therefore combines:

```json
"x-payment": { "mode": "none" },
"security": [{ "siwx": [] }],
"responses": {
  "402": { "description": "Authentication Required" }
}
```

This excerpt omits the success schema for readability; the complete fixture retains it. This combination requires separate treatment of payment evidence and authentication signaling.

The fixture adds the missing required jobId path parameter and a proposed OpenAPI Link from the creation response to the status operation:

```json
"pollJob": {
  "operationId": "jobs_status",
  "parameters": { "jobId": "$response.body#/jobId" }
}
```

The client should follow the documented job flow and evaluate the returned pollUrl under its origin policy. Repeating a paid creation call is not a substitute for polling.

The selected generation metadata exposes USD 0–10, while the guide lists USD 0.13–0.24. Preserve this discrepancy rather than presenting either range as a request-specific quote. The status schema leaves result unconstrained, so a consumer cannot infer that result.imageUrl is always present from a guide example. [S1][S2]

**What this tests:** a final description must include the operations needed after purchase, even when those operations require authentication but no new payment. It must distinguish job acceptance from completed output. Schema presence does not guarantee that every useful output field is specified.

No deployment architecture is inferred from these documents. The fixture uses direct publication; an authorized provider could supply equivalent annotations through an overlay.

Files: `examples/stablestudio/well-known.json`, `final.openapi.json`, and `changes.json`.



## StableUpload with a separate transfer step

The selected example includes six operations: purchase a file slot, list uploads, read upload metadata, purchase a site slot, request a site replacement upload, and activate a site. Paid purchase and wallet-authenticated owner actions are distinct. [U1][U2]

An illustrative file-slot request is:

```json
{
  "filename": "report.pdf",
  "contentType": "application/pdf",
  "tier": "10mb"
}
```

The documented flow first purchases the slot, then transfers bytes to the returned destination. The client uses the returned upload method. The upload target expiry and the hosted file expiry describe different lifetimes. A purchased slot does not establish that the file has been uploaded successfully. [U1][U2]

The fixture preserves the source input and output schemas. It converts the documented `:uploadId` route notation to OpenAPI `{uploadId}` and adds a required string parameter. It also gives the site POST and PUT operations distinct IDs. All changes are listed separately from the original snapshot.

This case clarifies the origin restriction. Publishing an API contract on the merchant origin does not require every file URL returned by that API to use the same origin. A runtime upload URL may carry a short-lived capability. The client must check its destination and purpose, and must not forward wallet-authentication headers or unrelated credentials to it.

A future workflow profile can make upload-method branches and lifecycle transitions easier to evaluate. For this proposal, preserve the service’s declared schemas and explain the sequence. Do not invent an expiry, retention guarantee, or output field that the source does not provide.

**What this tests:** discovery must describe the work purchased, the next operation, and any separate authentication. Payment, upload completion, activation, and public availability are different states.

Files: `examples/stableupload/well-known.json`, `final.openapi.json`, and `changes.json`.



## Technical appendix on provider composition

This controlled example uses the same StableTravel search operation to test a second publication workflow. It does not claim that StableTravel uses a managed gateway.

The application owner supplies a base OpenAPI description containing the operation’s inputs and successful response. The provider supplies an Overlay 1.1 document that adds the payment response and payment metadata introduced by its policy. The merchant’s authorized build applies it and publishes the final description.

The complete overlay is in the example bundle. Its target and proposed summary are:

```json
{
  "target": "$['paths']['/api/google-flights/search']['get']",
  "update": {
    "x-payment": {
      "mode": "required",
      "protocols": [
        { "name": "x402" },
        { "name": "mpp" }
      ]
    }
  }
}
```

The complete file also restores the source x-payment-info object and 402 response. The output is checked against the independently extracted direct-publication operation. Inputs, outputs, and payment annotations must agree.

The provider owns the accuracy of its integration input. The publisher owns the approved release. The merchant can delegate both generation and hosting; responsibility does not require manual editing or a merchant-operated build server.

Publication must fail when a payment target no longer matches, when sources contradict each other, or when required application schemas are damaged. Always start composition from the selected base revision. Overlay updates can append arrays; starting fresh does not resolve conflicts between two overlays in one build. The production profile still needs explicit duplicate-offer and field-ownership checks.

A facilitator can supply information about supported mechanisms. That alone cannot establish the merchant’s actual prices, payable routes, or application schema. Only include behavior the application or authorized provider has configured.

**The client receives the same kind of final artifact in both paths.** It does not need to know who wrote an overlay or how the document was built.

Files: `examples/managed-provider/base.openapi.json`, `provider.overlay.json`, and `expected.openapi.json`.



## Technical appendix on the example format

The first profile covers HTTP APIs described by OpenAPI 3.1. It leaves x402’s core payment types unchanged. A client begins with a known service origin, reads an entry document, then reads a complete OpenAPI artifact. It does not execute an overlay.

The examples use this provisional entry format and path. The working group can later adopt an ARD profile or another agreed envelope without changing who publishes the final API contract.

```json
{
  "discoveryVersion": "0.1",
  "apis": [{
    "id": "stabletravel",
    "url": "https://stabletravel.dev/discovery/releases/example-2026-09-19/openapi.json"
  }]
}
```

The proposed path is `/.well-known/x402-discovery`. Neither this path nor the example release URLs are claimed to exist on the services. The bundle maps them to local files.

Publish the entry document and final description without payment or credentials. Use HTTPS, cache validators, and explicit OpenAPI server URLs. Keep API identity stable when a release URL changes. Each operation needs a unique operationId and correctly declared path parameters.

The example `x-payment` extension is a proposed summary, not an existing x402 extension. Its modes describe whether a new payment is required for the operation: required, conditional, or none. Missing metadata means unknown. Authentication stays in OpenAPI security requirements. A mode of none does not mean anonymous access or permission to call the operation.

**HTTP 402 alone is not a payment classification.** An authentication-only challenge can use that status. Reject a free-access claim when it conflicts with actual payment terms, not merely because a 402 response exists.

Preserve existing payment metadata with its actual schema and provenance. The live challenge determines the request-specific terms; the client still applies its budget, recipient, asset, and protocol policy. A static description never authorizes payment.

For the initial profile, the entry document, OpenAPI artifact, and effective API server URLs share an origin. Returned upload, download, or result URLs are runtime data. They need separate client checks and must not be mistaken for catalog delegation.



## Technical appendix on source findings

| Finding | Change to the proposal |
| --- | --- |
| Direct publication already has the needed API and payment facts | Make overlays optional and define final-output conformance |
| Authenticated polling can return 402 without a new payment | Classify from payment and authentication evidence, not status alone |
| Stable services use price and protocols inside x-payment-info | Do not identify an extension schema from its name alone; require an explicit profile or version before generic interpretation |
| Display prices use fractional USD strings | Keep display estimates separate from native atomic payment amounts |
| Route templates and operation IDs can be incomplete or ambiguous | Validate route correspondence, parameter declarations, and unique IDs |
| Payment may buy a job or an upload slot | Describe subsequent actions and distinguish acceptance from completion |
| Runtime file destinations may be external | Separate discovery-origin rules from runtime destination policy |

The downloaded OpenAPI snapshots contain 45 StableTravel operations, 36 StableStudio operations, and 11 StableUpload operations. These are method-and-path counts from the captured files, not a claim that every live route is covered. The worked examples select 3, 2, and 6 operations respectively.

All source operations were inventoried. The checks found duplicate site and site-domain operation IDs in StableUpload, colon-style route notation for its metadata endpoint, and missing jobId path declarations in StableStudio. StableTravel’s usage-guide comparison exposed the trip-route disagreement. The examples address selected cases; they do not silently repair the full source documents.

The Stable x-payment-info shape differs from the offers-oriented [Payment Authentication discovery draft](https://paymentauth.org/draft-payment-discovery-01.txt). The examples preserve the source object; they do not claim conformance to that draft. No merchant payout address, network selection, x402 version, or complete PaymentRequirements object is invented from an empty x402 metadata object.

The source descriptions provide useful discovery evidence. They do not prove the services’ internal SDK configuration, facilitator choice, current runtime responses, or successful settlement.



## Evidence and next decisions

The bundle includes the complete retrieved OpenAPI and usage-guide snapshots for the three selected services, a source hash inventory, proposed example manifests and final descriptions, a managed-provider overlay, and repeatable offline checks. StableTravel’s docs page is a Swagger viewer of its OpenAPI document. StableStudio’s agents.txt was also reviewed. Upstream model-provider tutorials are not part of these merchants’ API contracts.

**Validation result:** 18 targeted offline checks passed. They cover selected structural requirements, same-origin references, preservation of native payment metadata, authenticated no-new-payment behavior, the asynchronous link, direct-versus-composed equality, and rejection of selected defects.

The checker supports only the member-selection JSONPath and update shapes used by these fixtures. It is not a full OpenAPI validator or a conforming general Overlay implementation. No paid operation, upload, booking, or payment was executed. Runtime compatibility and operator approval remain separate gates.

For adoption, the working group needs to settle the entry envelope and suffix; the payment-summary schema and its relationship to existing extensions; publisher and client failure behavior; and a conformance suite using production-grade OpenAPI and Overlay tooling. ARD reuse remains a comparison to perform, not a dependency that prevents direct publication now.

The discussion decision concerns the publication model. Adoption of an interoperable specification requires the remaining format and conformance work above.

### Sources

- T1  https://stabletravel.dev/openapi.json
- T2  https://stabletravel.dev/llms.txt
- S1  https://stablestudio.dev/openapi.json
- S2  https://stablestudio.dev/llms.txt
- U1  https://stableupload.dev/openapi.json
- U2  https://stableupload.dev/llms.txt
- OpenAPI Overlay 1.1  https://spec.openapis.org/overlay/v1.1.0.html
- x402 core and authoring guidance  https://github.com/x402-foundation/x402/tree/c8c71f244c0d45a6a4fd990a96c69aa34781cd05

Service documents captured on 19 September 2026. The source files and example change records distinguish observed documentation from proposed changes.
