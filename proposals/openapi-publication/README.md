# OpenAPI publication proposal

Start with [the proposal](proposal.md). It asks the WG to agree on a publication model: a well-known entry document points to final OpenAPI descriptions, produced directly or through optional provider overlays. Format choices remain open.

Read [the worked examples](worked-examples.md) for the supporting evidence and limitations.

## Contents

- `examples/stabletravel`, `examples/stablestudio`, and `examples/stableupload`: provisional well-known manifests, selected final OpenAPI descriptions, and explicit change records.
- `examples/managed-provider`: a base description, an Overlay 1.1 document, and expected output for a controlled comparison with direct publication.
- `sources`: public OpenAPI and usage-guide snapshots captured on 19 September 2026, retained for reproducible review. Source URLs appear in `evidence.json` and the worked examples. They are third-party source material, not WG-authored specifications.
- `evidence.json`: OpenAPI source hashes and operation counts.
- `build_examples.py` and `check_examples.py`: Python standard-library scripts for reproduction and targeted checks.

## Run offline

From this directory, with Python 3:

```sh
python3 build_examples.py
python3 check_examples.py
```

The scripts read local snapshots, make no network requests, and execute no payments. The checker writes `check-results.json`. Eighteen targeted checks cover selected structure, metadata preservation, publication composition, and selected failure cases. It is not a full OpenAPI validator or a general Overlay implementation. No dependencies are required.

The managed-provider scenario is illustrative; it does not claim that StableTravel uses a gateway. All proposed service corrections need operator confirmation. The provisional manifest URLs are not deployed: map each URL to `final.openapi.json` in the same service folder for offline review. The proposed publication location is `/.well-known/x402-discovery`; its name and format remain open.

The examples preserve the observed `x-payment-info` objects and add an experimental `x-payment` summary. StableStudio ownership proofs and embedded guidance are omitted from the modified artifacts; no proof validation or portability to a changed document is claimed. Original snapshots remain unchanged.

## Review and discussion

Use the proposal for publication-model decisions and the examples for technical review. A Google Docs copy can support comments; accepted changes should be reflected in these versioned Markdown files. Native Google Docs publication is separate from this repository contribution.
