# Migration fixture: a real incumbent → `x402Version: 2`

This directory holds a **before/after pair** captured from one production host, so
the section 8.2 / 8.3 transition is checkable rather than described.

| file | what it is |
| --- | --- |
| `incumbent-legacy.json` | the incumbent manifest, **verbatim** — as the host serves it at `/.well-known/x402` |
| `incumbent-v2.well-known-x402.json` | the `x402Version: 2` rendition of the same host |

`proposal/test_discovery.py` asserts three things about the pair:

1. `incumbent-legacy.json` is **rejected** by `domain-discovery.schema.json` (it is not
   a positive example);
2. `incumbent-v2.well-known-x402.json` **passes**;
3. the transition is **mechanical** — for every entry the `v2` `path` is the
   incumbent `url`'s path, `method` carries into `methods`, `description` is
   preserved, and every incumbent root key the schema does not admit lands in
   `extensions` with its value unchanged.

## Provenance

Captured `2026-10-14T11:0xZ` from `https://minia2a.uk/.well-known/x402`
(76 resources, 24 root keys). The `accepts` terms in the v2 rendition are a
snapshot of each endpoint's live `402` challenge — `scheme` `exact`, CAIP-2
network `eip155:8453`, USDC on Base, per-endpoint atomic `amount`, and the host's
`payTo` as `recipient`. They are not derived from the incumbent, because the
incumbent declares no payment terms at all: that is the point of the version
break (section 8.2, "forcing clients into speculative execution and reactive HTTP
402 challenge negotiation").

## One wrinkle worth recording

The incumbent's own root literal is **`x402Version: 2`**, not `1`. It has carried
that value since at least 2026-08-15. So this fixture is not the simple
"`x402Version: 1` host" case — it is the subtler one the schema is meant to catch:
a host that **already claims version 2 while shipping the legacy entry shape**
(`{url, method, description}`, extra root keys).

It is still rejected, and not by the version `enum` — rejection comes from
`additionalProperties: false` at the root and `required: [path, accepts]` on each
resource. The `x402Version` literal alone is not a conformance signal; the entry
shape is. (The same collision arises in the other direction for hosts whose
`x402Version` tracks the x402 *protocol* version rather than this manifest schema.)
