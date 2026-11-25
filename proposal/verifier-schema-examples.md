# Worked examples

## 1. nohumans.directory

Free record lookup at `GET /v1/resolve?url=`, paid verdict over x402 at `GET /v1/listings/{id}/verdict`. Today emits `pay | caution | avoid` with prose reasons; under this schema that becomes the `recommendation` object citing a `verdict` built from the closed reason set.

## 2. Generic example

```json
{
  "verdict": "false",
  "reason": "wrong-domain",
  "evidence": "probe",
  "observed_at": "2026-09-28T18:40:00Z",
  "checked_at": "2026-09-28T18:40:00Z",
  "untested": ["purchase"],
  "accepts_index": 0,
  "detail": {
    "field": "extra.name",
    "expected": "USD Coin",
    "got": "USDC"
  },
  "digest": {
    "scheme": "exact",
    "network": "eip155:8453",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x2076045...",
    "amount": "10000",
    "extra": { "name": "USDC", "version": "2" }
  },
  "mapping": {
    "entry": "exact/eip155:8453/0x833589f...",
    "contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "read_at": "2026-09-28T00:00:00Z"
  }
}
```

## 3. Paddock (verify_before_pay)

Reads the live 402 and decodes payTo/chain/asset off the challenge itself, biased toward inconclusive over a false pass.

- settled-under-terms / probe-ok ← route: true, split by whether an independent paid-fulfillment record exists
- wrong-domain, terms-mismatch ← route: false, with the mismatched field named
- inconclusive ← route_state: "inconclusive", always carrying untested rather than defaulting to a pass
- observed_at ← timestamp of the strongest check that ran; checked_at ← timestamp of this call regardless of level reached
- digest ← the decoded challenge fields
- `attestation` ← `attest: true` issues a signed record under Paddock's own domain (paddock.finance), distinct from the checked resource's domain. `subject.resource_domain` is the seller's domain from the resolved challenge; `subject.verifier_domain` is paddock.finance; `key_url` and `record_url` resolve under paddock.finance; `valid_until` bounds the attestation's freshness.

## 4. Relayed purchase, relationship disclosed, method pinned

A verifier at `verifier.example.org` did not buy the resource itself. It holds a paid-call record signed by a source at `checker.example.net`, whose key is served from that same domain, so a client can check the record offline without calling either party. The verification was paid for by the client. The domains are placeholders and the digest is illustrative.

```json
{
  "verdict": "true",
  "reason": "settled-under-terms",
  "evidence": "purchase",
  "purchase_by": "relayed",
  "purchase_source": {
    "source_domain": "checker.example.net",
    "record_url": "https://checker.example.net/records/7f3a",
    "key_url": "https://checker.example.net/.well-known/checker-keys.json",
    "key_id": "checker-2026-10"
  },
  "method_digest": "sha256:9870d2f640b01c84bee0722b1c1aa565c76af995205fb42a9695b30eb82f27e5",
  "observed_at": "2026-10-20T09:00:00Z",
  "checked_at": "2026-10-23T08:00:00Z",
  "untested": [],
  "accepts_index": 0,
  "attestation": {
    "key_url": "https://verifier.example.org/.well-known/jwks.json",
    "record_url": "https://verifier.example.org/attestations/41",
    "subject": {
      "resource_domain": "seller.example.com",
      "verifier_domain": "verifier.example.org"
    },
    "valid_until": "2026-10-30T08:00:00Z",
    "relationship": ["paid-by-client"]
  }
}
```

Had the record been confirmable only by asking `checker.example.net`, or only against a key carried in the record itself, the same verifier would report `evidence: "probe"` (or `terms`), omit `purchase_by` and `purchase_source`, and list `purchase` in `untested`.
