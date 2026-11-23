# x402 Domain Discovery: comparing the three proposals

**Prepared by:** Akash Balasubramani (Chair)<br>
**Date:** 5 October 2026

## How this works

This file lines up the three discovery proposals topic by topic, so the group can decide what goes into v1 of the spec. Each row is one topic. The columns show how each proposal handles it, a starting suggestion, and a blank Decision column that we fill in on the call.

- **Comments:** leave a review comment on any row you disagree with. Since this was shared just before the 5 Oct call, comments are welcome until the next call.
- **On the call:** we walk through every row together. Each row ends as **Accept**, **Reject** or **Defer**. Anything that needs more time moves to a GitHub issue.
- **After the call:** decisions are recorded in this file, and agreed changes go into Patrick's PR #4, which we agreed on the last call to use as the base. Open questions become GitHub issues.

The Starting suggestion column is the chair's suggestion to start discussion, not a final ruling. Where a position is marked *withdrawn*, its author has dropped it.

**Which version is compared.** Patrick revised [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) on 1 October, after the 21 Sep call. This file compares PR #4 at commit cec8145. Cells marked **(changed 1 Oct)** are positions that changed in that revision. They are Patrick's updated proposal and have not yet been discussed by the group.

**The three proposals**

| Short name | Document | Authors | Version compared |
| :---- | :---- | :---- | :---- |
| **Rohin & Aadil** | [x402 Domain Discovery](https://docs.google.com/document/d/1iF88Zk3jHmLwdmMsB8vjPHd_zZZ5STcEU0uq-B7037c/edit) | Rohin Lohe, Aadil Ahmed | Draft of 25 Aug |
| [**PR #4**](https://github.com/x402-foundation/wg-domain-discovery/pull/4) **(Patrick)** | [Propose x402 domain discovery through OpenAPI](https://github.com/x402-foundation/wg-domain-discovery/pull/4) | Patrick Barattin | Commit cec8145, 1 Oct |
| **Draft V1 (Akash)** | [x402 Domain Discovery V1 Draft Specification](https://docs.google.com/document/d/1AxNhnJkNvb3bjRyLIUY0KwH3JCD-74-4QngIT9YYn14/edit) | Akash Balasubramani | Version reviewed on 9 Sep |

Background: Rohin's [principles doc](https://docs.google.com/document/d/1gByGQRF7PH_St2Y_DLewo_uUeOQPJPugLywQs3PXQ4c/edit).

## Process agreed on 21 Sep

- The spec is written on GitHub in wg-domain-discovery. Slack is for async discussion.
- Patrick's [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) is the base text. Ideas from the other proposals come in as branches or PRs against it.

## 1. Already agreed: confirm together

Rows 1 to 5 were agreed on 21 Sep without objection. Row 6 is new: after the revision of PR #4, all three proposals now agree on it. Unless someone comments or raises it on the call, we will confirm all six as Accepted.

| # | Topic | Rohin & Aadil | PR #4 (Patrick) | Draft V1 (Akash) | Starting suggestion | Decision |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | Discovery is advisory. The live 402 response is authoritative. | Yes | Yes | Yes | Accept |  |
| 2 | Not at the server root, not named openapi.json | Under /.well-known/ | Under /.well-known/ | GET /openapi.json at root (*withdrawn*) | Accept |  |
| 3 | Payment fields use x402's own shape, not MPP's | accepts with x402 field names | accepts as a static subset of x402's PaymentRequired, every field keeping its runtime name **(changed 1 Oct)** | MPP-style offers with intent, method (*withdrawn*) | Accept |  |
| 4 | The spec defines only the final published OpenAPI document. Overlays are optional. | Published through the origin's OpenAPI process or a monetization SDK | Direct or overlay. Both give the same document. Clients never apply overlays. | Overlay model for managed providers | Accept |  |
| 5 | A price range can be advertised | upto: amount is the max, extra.minAmount the min | minAmount and maxAmount on each payment option **(changed 1 Oct)** | min and max | Accept (whether amounts are required is row 10) |  |
| 6 | Amounts are in the asset's atomic units, as in the live 402 | Yes, amount in atomic units | Yes, bounds in atomic units of asset **(changed 1 Oct; was a fiat range like USD 0.01)** | Yes, smallest denomination | Accept |  |

## 2. To decide

Row 7 comes first because most of the others depend on it. Rows 20 to 22 are each covered by only one proposal. For each, we decide whether it goes into v1 or follows straight after.

| # | Topic | Rohin & Aadil | [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) (Patrick) | Draft V1 (Akash) | Starting suggestion | Decision |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 7 | Well-known path, and what is served there | /.well-known/x402.json is the OpenAPI document itself | Bare /.well-known/x402: a small entry with x402Version and links to OpenAPI documents. One document per host, which can also carry host-wide fields. **(changed 1 Oct; was /.well-known/x402.json)** | (*withdrawn*, see row 2) | PR #4. Melchiorre's 22 Sep sweep (on PR #4) found 786 hosts already serving an x402 manifest at /.well-known/x402, so the entry has to be agreed with the authors of that manifest (x402 PR #2979). Patrick has offered to align. |  |
| 8 | Name of the per-operation field | x-payment-info | x-x402 | x-payment-info | x-payment-info, with a marker inside it saying the content is x402 |  |
| 9 | x402 only, or open to other payment protocols | Other protocols out of scope | x402 only, and HTTP only. MCP and A2A are out of scope. | Designed to fit MPP (*withdrawn*) | x402 only for v1, under a key that leaves room for others. Goes into the charter's scope. |  |
| 10 | Are amounts required? | Yes. amount is required on every payment option. | No. Bounds are optional. An empty x-x402 means the operation uses x402 without advertising terms. **(changed 1 Oct)** | Yes, but null means the price is set at request time | Optional. A price set per request then needs no made-up number. |  |
| 11 | Required fields in each payment option | scheme, network, asset, amount, payTo all required | scheme and network required. asset required only with amount bounds. payTo removed: the recipient comes from the live 402. **(changed 1 Oct)** | Optional settlement config, including a stealth payout | PR #4 |  |
| 12 | How discovery is versioned | No version field | x402Version on the entry. Discovery is part of the x402 HTTP transport spec. The separate discoveryVersion option is dropped. **(changed 1 Oct)** | Date-based x-discovery.version on the document | PR #4 |  |
| 13 | Version on each operation | None | Removed. The version is set once, on the entry. Rules for several versions in one entry are still to be defined. **(changed 1 Oct; was on each operation)** | Document level only | Open. Lindsay supported per-operation versions on 21 Sep and has a use case that needs more than one version. Decide once that case is shared. |  |
| 14 | Extensions such as sign-in-with-x | Clients ignore unknown extensions | An extensions object keyed by extension ID, the same shape as the live 402 **(changed 1 Oct; was a list)** | Declared extensions with namespaced IDs | PR #4 |  |
| 15 | What a client does when the live price is outside the advertised range | Neither amount nor minAmount is an expected or guaranteed charge | The live amount SHOULD fall within the bounds. Clients MAY flag the operation or decline to pay. maxAmount is not a guaranteed cap. | A staleness signal for registries | PR #4: bounds are descriptive, and clients may apply their own policy. Raised in review on PR #4. |  |
| 16 | An operation with no payment annotation | A payable operation needs both a 402 response and x-payment-info. Having only one is nonconformant. | Missing information means unspecified, never free | Payable only if it has both a 402 response and x-payment-info | Write explicitly that a missing annotation MUST NOT be read as "free". Raised in review on PR #4. |  |
| 17 | Ownership and identity (proving who controls the domain or payout address) | Not covered | Out of scope, left to the Identity WG **(added 1 Oct)** | Notes deployed ownershipProofs. The proof format is left to the Identity WG. | Out of scope for v1. Coordinate with the Identity WG. The charter's scope will match. |  |
| 18 | Which operations an entry can describe | Every servers URL must be on the same origin as the document | Annotations apply only to operations on the entry's origin. The OpenAPI document itself may be hosted elsewhere, e.g. by a provider. **(added 1 Oct)** | Not covered | PR #4. It still lets a managed provider host the document. |  |
| 19 | Do x- fields imply the OpenAPI project endorses them? | Uses x- fields. Aadil passed on this concern on the 21 Sep call. | Uses x- fields. Patrick and Ethan read x- as OpenAPI's standard extension mechanism. | Uses x- fields | Acceptable, unless a source for the concern is shared before the call |  |
| 20 | Sites with thousands of pages, e.g. /news/{slug} | Atom feed content catalog | Not covered | Not covered | Open: optional section in v1, or a follow-on proposal. |  |
| 21 | Endpoint lifecycle | deprecated: true | deprecated: true, then remove from the next publication | x-lifecycle: sunset date, successor, removed-endpoint records | Open: deprecated: true only, or add lifecycle fields in v1. |  |
| 22 | Service and host-wide metadata (description, categories, facilitators) | info.description, info.contact.url | The entry allows host-wide fields, but defining them is left to host-level proposals such as #2979 **(changed 1 Oct)** | Categories and docs links | Open: standard OpenAPI info only, or add categories and docs links. Host-wide fields agreed with #2979. |  |

## 3. Smaller differences, to settle on GitHub

These do not need call time. Each can become a comment or issue on PR #4.

- **Caching:** Rohin & Aadil says publishers SHOULD send ETag and Last-Modified. [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) says they MAY send Last-Modified. V1 recommends Cache-Control with a 300-second max age.
- **Authentication:** all three use OpenAPI security. V1 adds a table of three endpoint classes: public, free but authenticated, and paid. [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) allows an authentication-only operation that advertises extensions without payment options.
- **Pricing basis:** only Rohin & Aadil has pricingBasis (per-token, per-second, per-byte).
- **Validation tooling:** only [PR #4](https://github.com/x402-foundation/wg-domain-discovery/pull/4) includes a JSON schema and an example checker.
- **Example fixes:** some JSON examples in Rohin and Aadil's doc do not parse. Fixes will be sent as suggested edits.
