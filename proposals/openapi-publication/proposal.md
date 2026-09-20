# Domain discovery for x402 services

## One entry point and two publication paths

Discussion proposal for the x402 Domain Discovery Working Group
19 September 2026

### The decision

We propose a well-known entry document that points to a final OpenAPI description. Support two publication paths: an application publishes the description directly, or an authorized build composes it from a base description and provider overlays. In both cases, agents read the final description.

**The merchant authorizes publication. An overlay is optional.**

### The problem

Given an API’s domain, an agent needs a predictable way to find its operations, inputs, outputs, payment requirements, and authentication requirements. The entry document provides the starting point. OpenAPI describes the operations. Payment metadata helps the agent assess supported payment options; the live challenge supplies the request-specific terms.

The publication model must work for a developer who embeds the x402 SDK and uses a facilitator, as well as a merchant who uses a managed gateway. Requiring every merchant to write an overlay would add work without improving the description available to the agent.

### How it works

```text
Application and SDK configuration ----> Final OpenAPI
Base OpenAPI + provider overlay ------> Final OpenAPI

Agent --> Well-known entry document --> Final OpenAPI
```

The publisher applies overlays before publication. Agents do not need to retrieve or execute them. The final description includes application behavior and any behavior introduced by an authorized provider.

### Who is responsible

| Role | Responsibility |
| --- | --- |
| Application developer | Describe routes, inputs, outputs, and behavior configured in the application or SDK |
| Managed provider | Describe the payment or gateway behavior it introduces; an overlay can carry these additions |
| Merchant or authorized publisher | Approve, validate, and publish a final description that matches the deployed service |
| Facilitator | Verify or settle payments under its protocol role; this role does not automatically include API documentation |

The merchant can delegate generation and hosting. Responsibility does not require manual editing or a merchant-operated build server.



## Agreement requested from the group

### Three questions

- Do we agree on a well-known entry point that references final OpenAPI descriptions?
- Do we agree that direct publication and overlay composition are both valid publication paths?
- Should we evaluate an ARD publication profile before defining a new entry format?

Agreement on these questions would establish the publication model. It would not approve the provisional path, fields, or payment extension in the examples.

### Scope of the first profile

Start with HTTP APIs described by OpenAPI 3.1. Publish both paid operations and operations that need no new payment, including follow-up operations required to complete a purchased job. Serve discovery documents without payment or credentials. A static description does not authorize payment.

For the initial profile, we propose that the entry document, final OpenAPI artifact, and effective API server URLs share an origin. This is a scope limit for discussion. A later profile can address delegated hosts and documentation CDNs. Runtime upload and result URLs need separate client checks.

Keep payment and authentication separate. A documented HTTP 402 response can request wallet authentication without a new payment. Payment classification must use the documented semantics, not the status code alone.

### What the examples demonstrate

| Example | Lesson |
| --- | --- |
| StableTravel | A final API description can be published directly without an overlay |
| StableStudio | Paid creation and authenticated polling are separate operations |
| StableUpload | Payment can start a workflow without completing the work |

The examples use captured public documentation and propose publication artifacts. They are not merchant-approved deployments or evidence of the services’ internal SDK or gateway architecture. A controlled provider-overlay example produces the same selected operation as direct publication.

### Choices that remain open

The group still needs to choose the entry envelope and well-known suffix, decide how payment summaries relate to existing extensions, and define publisher and client failure behavior. The example `x-payment` extension is experimental. Agreement on the publication model does not require adopting it.

The next technical step is to compare an ARD profile with the small example manifest, then validate both publication paths with standard OpenAPI and Overlay tooling. Conflicting overlays and runtime compatibility need further proof before normative adoption. The accompanying 18 checks are limited offline checks, not a conformance certification.

## Supporting material

See [worked examples](worked-examples.md) for StableTravel, StableStudio, StableUpload, and provider composition. The [README](README.md) explains the artifacts, evidence, and offline checks. These examples inform a discussion proposal; no format in this folder is an adopted WG standard.
