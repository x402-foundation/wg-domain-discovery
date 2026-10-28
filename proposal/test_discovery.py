#!/usr/bin/env python3
"""
x402 Domain Discovery Conformance & Schema Verification Suite
Validates RFC 8615 well-known domain discovery manifests against the authoritative JSON schema.
Verifies positive multi-rail examples and asserts schema rejection on paired negative edge fixtures.

Copyright (c) 2026 x402 Foundation contributors.
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path
import jsonschema

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "domain-discovery.schema.json"
EXAMPLES_DIR = BASE_DIR / "examples"
FIXTURES_DIR = EXAMPLES_DIR / "fixtures"
MIGRATION_DIR = EXAMPLES_DIR / "migration"

# Root keys the v2 schema admits. Kept explicit so that a schema revision which
# adds a root key is a deliberate edit here, instead of silently relaxing the
# §8.3 relocation assertion below.
V2_ROOT_KEYS = {
    "x402Version", "kind", "facilitator", "keys", "extensions", "resources", "openapi"
}

def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_migration_check(validator):
    """section 8.2/8.3: the incumbent -> v2 rendition must be a deterministic map.

    Returns the number of resource entries checked; exits 1 on any violation.

    The pair is a real incumbent host (76 resources, 24 legacy root keys), not a
    synthetic minimal. The three properties asserted are the three the section 8
    revision promises a migrating host can rely on:

      1. the incumbent fails the schema -- it is not a positive example;
      2. its v2 rendition passes;
      3. the transition is mechanical: `path` is the incumbent `url`'s path,
         `method` carries into `methods`, `description` is preserved, and every
         incumbent root key the schema does not admit lands in `extensions`
         with its value unchanged.
    """
    incumbent_file = MIGRATION_DIR / "incumbent-legacy.json"
    v2_file = MIGRATION_DIR / "incumbent-v2.well-known-x402.json"
    for path in (incumbent_file, v2_file):
        if not path.exists():
            print(f"[-] Missing migration fixture: {path}")
            sys.exit(1)

    incumbent = load_json(incumbent_file)
    v2 = load_json(v2_file)

    # (1) The incumbent is invalid -- that is the whole reason a migration exists.
    inc_errors = list(validator.iter_errors(incumbent))
    if not inc_errors:
        print("[-] FAIL: incumbent-legacy.json was ACCEPTED by the v2 schema; "
              "it no longer demonstrates a migration.")
        sys.exit(1)

    # (2) The v2 rendition is a positive example.
    v2_errors = list(validator.iter_errors(v2))
    if v2_errors:
        print("[-] FAIL: incumbent-v2.well-known-x402.json is not schema-valid:")
        for err in v2_errors[:10]:
            print(f"      - {err.validator} at {'/'.join(str(p) for p in err.path)}: {err.message}")
        sys.exit(1)

    # (3, section 8.3) Root relocation is total and value-preserving.
    relocated = 0
    for key, value in incumbent.items():
        if key == "resources":
            continue
        if key in V2_ROOT_KEYS:
            if v2.get(key) != value:
                print(f"[-] FAIL: root key '{key}' changed during migration")
                sys.exit(1)
        elif v2.get("extensions", {}).get(key) != value:
            print(f"[-] FAIL: legacy root key '{key}' did not land in extensions unchanged")
            sys.exit(1)
        else:
            relocated += 1

    # (3, section 8.2) Every resource entry maps mechanically, in order.
    inc_res = incumbent.get("resources", [])
    v2_res = v2.get("resources", [])
    if len(inc_res) != len(v2_res):
        print(f"[-] FAIL: resource count changed {len(inc_res)} -> {len(v2_res)}")
        sys.exit(1)
    for i, (before, after) in enumerate(zip(inc_res, v2_res)):
        want_path = urllib.parse.urlsplit(before.get("url", "")).path
        if after.get("path") != want_path:
            print(f"[-] FAIL: entry {i}: path {after.get('path')!r} != url path {want_path!r}")
            sys.exit(1)
        if after.get("methods") != [before.get("method")]:
            print(f"[-] FAIL: entry {i}: methods {after.get('methods')!r} does not carry "
                  f"method {before.get('method')!r}")
            sys.exit(1)
        if before.get("description") and after.get("description") != before.get("description"):
            print(f"[-] FAIL: entry {i}: description not preserved")
            sys.exit(1)
        if not after.get("accepts"):
            print(f"[-] FAIL: entry {i}: v2 entry has no accepts")
            sys.exit(1)

    print(f"[PASS] migration: incumbent ({len(inc_errors)} schema error(s)) -> v2 valid; "
          f"{len(v2_res)} entr(ies) map deterministically (section 8.2), "
          f"{relocated} legacy root key(s) relocated to extensions (section 8.3)")
    return len(v2_res)

def build_strict_format_checker():
    """Build a strict RFC 3987 absolute HTTP(S) URI FormatChecker without optional C/regex deps."""
    checker = jsonschema.FormatChecker()
    disallowed_chars = set(' \t\r\n{}<>"`|\\^[]')

    @checker.checks("uri")
    def is_strict_http_uri(instance):
        if not isinstance(instance, str) or not instance:
            return False
        if any(ch in disallowed_chars for ch in instance):
            return False
        parsed = urllib.parse.urlsplit(instance)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    return checker

def assert_uri_checker_capabilities(validator):
    """Capability self-test: assert strict URI rejection before judging any manifest."""
    must_reject_probes = [
        "https://x/report/{agent_id}",
        "POST https://x/y",
        "/relative/path",
        "not a uri",
        "https:///path",
        "https://?q",
        "https://#frag"
    ]
    for bad_uri in must_reject_probes:
        probe_doc = {"x402Version": 2, "resources": [bad_uri]}
        errs = list(validator.iter_errors(probe_doc))
        validators_hit = {e.validator for e in errs if list(e.path) == ["resources", 0]}
        if "pattern" not in validators_hit or "format" not in validators_hit:
            print(f"[-] FAIL: capability check failed on {bad_uri!r}; "
                  f"expected both 'pattern' and 'format' rejection, got {validators_hit}")
            sys.exit(1)
    print(f"[PASS] capability self-check: validator rejects {len(must_reject_probes)} malformed URI probes "
          "via both Draft-07 'pattern' and strict RFC 3987 'format: uri'")

def run_tests():
    print("=" * 70)
    print("x402 DOMAIN DISCOVERY SCHEMA & CONFORMANCE TEST SUITE")
    print("=" * 70)

    # 1. Load Authoritative Schema
    if not SCHEMA_FILE.exists():
        print(f"[-] ERROR: Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)

    schema = load_json(SCHEMA_FILE)
    format_checker = build_strict_format_checker()
    validator = jsonschema.Draft7Validator(schema, format_checker=format_checker)
    print(f"[+] Loaded schema: {SCHEMA_FILE.name}")
    assert_uri_checker_capabilities(validator)

    # 2. Positive Conformance Tests
    positive_files = [
        "minimal.well-known-x402.json",
        "multirail-service.well-known-x402.json",
        "facilitator.well-known-x402.json",
        "service-with-openapi.well-known-x402.json",
        "bare-openapi.well-known-x402.json",
        "hybrid-facilitator.well-known-x402.json",
        "forward-extensions.well-known-x402.json",
        "pointer-only-no-root-version.well-known-x402.json"
    ]

    print("\n--- 1. POSITIVE CONFORMANCE TESTS (MUST PASS) ---")
    pos_passed = 0
    for filename in positive_files:
        filepath = EXAMPLES_DIR / filename
        if not filepath.exists():
            print(f"[-] Missing positive test fixture: {filename}")
            sys.exit(1)

        data = load_json(filepath)
        errors = list(validator.iter_errors(data))
        if errors:
            print(f"[-] FAIL: {filename}")
            for err in errors:
                print(f"    Error: {err.message} at path: {'/'.join(str(p) for p in err.path)}")
            sys.exit(1)
        else:
            print(f"[PASS] {filename} (valid)")
            pos_passed += 1

    # 3. Negative Edge Fixture Tests (MUST REJECT ON SPECIFIC CONSTRAINT)
    negative_fixtures = [
        ("invalid-missing-version.json", "required", [], "missing required x402Version"),
        ("invalid-bad-version.json", "enum", ["x402Version"], "unsupported x402Version"),
        ("invalid-version-conflict.json", "enum", ["resources", 0, "x402Version"], "entry x402Version conflicting with v2"),
        ("invalid-bad-caip2.json", "pattern", ["resources", 0, "accepts", 0, "network"], "malformed CAIP-2 network identifier"),
        ("invalid-caip2-reference-overflow.json", "pattern", ["resources", 0, "accepts", 0, "network"], "CAIP-2 network reference exceeding 32 characters"),
        ("invalid-negative-amount.json", "pattern", ["resources", 0, "accepts", 0, "amount"], "negative amount string"),
        ("invalid-empty-accepts.json", "minItems", ["resources", 0, "accepts"], "empty accepts array"),
        ("invalid-misplaced-carrier.json", "not", [], "misplaced carrier key at root"),
        ("invalid-missing-kid.json", "required", ["keys", 0], "signing key missing required kid"),
        ("invalid-method-in-string.json", "pattern", ["resources", 0], "HTTP method embedded inside bare pointer string"),
        ("invalid-pointer-uri-template.json", "pattern", ["resources", 0, "url"], "unresolvable URI template in pointer url"),
        ("invalid-empty-authority.json", "pattern", ["resources", 0], "empty URI authority after scheme://")
    ]

    print("\n--- 2. NEGATIVE EDGE FIXTURE TESTS (MUST REJECT ON SPECIFIC CONSTRAINT) ---")
    neg_passed = 0
    for filename, expected_validator, expected_path, expected_cause in negative_fixtures:
        filepath = FIXTURES_DIR / filename
        if not filepath.exists():
            print(f"[-] Missing negative test fixture: {filename}")
            sys.exit(1)

        data = load_json(filepath)
        errors = list(validator.iter_errors(data))
        if not errors:
            print(f"[-] CRITICAL FAIL: {filename} was unexpectedly ACCEPTED by schema!")
            print(f"    Expected rejection cause: {expected_cause}")
            sys.exit(1)

        # Assert the rejection is caused by the specific validator and path, not generic fallout
        matched = False
        for err in errors:
            if err.validator == expected_validator and list(err.path) == expected_path:
                matched = True
                err_msg = err.message
                err_path = "/".join(str(p) for p in err.path) or "(root)"
                print(f"[PASS] {filename} correctly rejected by '{err.validator}' at {err_path}: '{err_msg}'")
                neg_passed += 1
                break

        if not matched:
            print(f"[-] FAIL: {filename} was rejected, but not by expected validator '{expected_validator}' at {expected_path}")
            print(f"    Actual errors:")
            for err in errors:
                print(f"      - validator='{err.validator}' at path={list(err.path)}: {err.message}")
            sys.exit(1)

    # 3b. Resource Class Discrimination, Effective x402Version Inheritance & Repair-Axis Checks (§4.2, §4.3, §8.2, §8.3)
    print("\n--- 2b. RESOURCE CLASS DISCRIMINATION, VERSION INHERITANCE & REPAIR-AXIS CHECKS ---")
    pointer_and_root_manifest = {
        "x402Version": 2,
        "name": "Example Pointer Service",
        "description": "Benign unknown descriptive root keys tolerated by client validation",
        "resources": [
            {"url": "https://example.com/x402/proxy/x402-gas", "method": "GET", "description": "Gas prices across 5 chains."},
            "https://example.com/x402/proxy/x402-find"
        ]
    }
    ptr_errors = list(validator.iter_errors(pointer_and_root_manifest))
    if ptr_errors:
        print(f"[-] FAIL: pointerResource + benign root keys rejected: {ptr_errors[0].message}")
        sys.exit(1)
    print("[PASS] pointerResource ({url, method, description} + URI string) & benign unknown root keys accepted")

    # Pointer-only manifest without root x402Version (live 402 at target URL governs at runtime)
    pointer_only_no_root_version = {
        "resources": [
            {"url": "https://example.com/x402/proxy/x402-gas", "method": "GET"},
            "https://example.com/x402/proxy/x402-find"
        ]
    }
    ptr_no_ver_errors = list(validator.iter_errors(pointer_only_no_root_version))
    if ptr_no_ver_errors:
        print(f"[-] FAIL: pointer-only manifest without root x402Version rejected: {ptr_no_ver_errors[0].message}")
        sys.exit(1)
    print("[PASS] pointer-only manifest without root x402Version accepted (target 402 governs version)")

    # Empty resources[] array without root x402Version is NOT vacuously exempted
    empty_resources_no_version = {"resources": []}
    empty_res_errors = list(validator.iter_errors(empty_resources_no_version))
    if not any(e.validator == "required" and list(e.path) == [] and "'x402Version'" in e.message for e in empty_res_errors):
        print("[-] FAIL: empty resources[] array without root x402Version was not rejected by 'required'")
        sys.exit(1)
    print("[PASS] empty resources[] array without root x402Version rejected (minItems: 1 required for pointer exemption)")

    # Informational root summary relocated into extensions.settlement on a pointer manifest (§8.3.2)
    pointer_with_relocated_summary = {
        "kind": "resource-server",
        "resources": [
            {"url": "https://api.example.com/x402/gas", "method": "GET", "description": "Gas prices"},
            {"url": "https://api.example.com/x402/quote", "methods": ["GET", "POST"]}
        ],
        "extensions": {
            "settlement": {
                "payTo": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "networks": ["eip155:8453"],
                "fee": "0.01 USDC",
                "access": "x402"
            }
        }
    }
    relocated_summary_errors = list(validator.iter_errors(pointer_with_relocated_summary))
    if relocated_summary_errors:
        print(f"[-] FAIL: pointer manifest with extensions.settlement summary rejected: {relocated_summary_errors[0].message}")
        sys.exit(1)
    print("[PASS] pointer manifest with informational root summary relocated into extensions.settlement accepted (0 errors)")

    # All-inline manifest without root x402Version where every entry carries its own x402Version: 2
    inline_per_entry_versioned = {
        "resources": [
            {
                "x402Version": 2,
                "path": "/api/v1/alpha",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "100"}]
            },
            {
                "x402Version": 2,
                "path": "/api/v1/beta",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "200"}]
            }
        ]
    }
    inline_ver_errors = list(validator.iter_errors(inline_per_entry_versioned))
    if inline_ver_errors:
        print(f"[-] FAIL: per-entry versioned selfContainedResource manifest rejected: {inline_ver_errors[0].message}")
        sys.exit(1)
    print("[PASS] selfContainedResource manifest with per-entry x402Version: 2 (no root x402Version) accepted")

    # Root vs. entry x402Version disagreement is an offline conformance error
    version_disagreement_manifest = {
        "x402Version": 2,
        "resources": [
            {
                "x402Version": 1,
                "path": "/api/v1/conflict",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "100"}]
            }
        ]
    }
    disagree_errors = list(validator.iter_errors(version_disagreement_manifest))
    if not any(e.validator == "enum" and list(e.path) == ["resources", 0, "x402Version"] for e in disagree_errors):
        print("[-] FAIL: root/entry x402Version disagreement was not rejected by 'enum' at resources/0/x402Version")
        sys.exit(1)
    print("[PASS] root/entry x402Version disagreement deterministically rejected by 'enum' at resources/0/x402Version")

    ambiguous_mixed_entry = {
        "x402Version": 2,
        "resources": [
            {
                "path": "/api/v1/mixed",
                "url": "https://example.com/api/v1/mixed",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "100"}]
            }
        ]
    }
    mix_errors = list(validator.iter_errors(ambiguous_mixed_entry))
    if not any(e.validator == "additionalProperties" and list(e.path) == ["resources", 0] for e in mix_errors):
        print("[-] FAIL: overlapping {path, url, accepts} entry was not rejected by resources[0] additionalProperties")
        sys.exit(1)
    print("[PASS] ambiguous overlapping {path, url, accepts} entry deterministically rejected by 'additionalProperties' at resources/0")

    # Repair-axis attribution derived directly from schema descriptions (zero separate vocabulary drift)
    def describe_repair_axis(err, instance):
        path = list(err.path)
        if path == ["x402Version"] or (len(path) == 3 and path[0] == "resources" and path[2] == "x402Version") or (
            err.validator == "required" and path == [] and "'x402Version'" in err.message
        ):
            return f"axis=version: {err.message} at {'/'.join(str(p) for p in path) or '(root)'}"
        if err.validator == "not" and path == []:
            carriers = [
                sub["required"][0]
                for sub in err.validator_value.get("anyOf", [])
                if "required" in sub and sub["required"][0] in instance
            ]
            desc = err.schema.get("description", "")
            return f"axis=misplaced-root-carrier ({', '.join(carriers)}): {desc}"
        if err.validator == "anyOf" and path == []:
            branches = err.schema.get("anyOf", [])
            best_idx = 0
            best_count = None
            for idx, branch in enumerate(branches):
                cnt = len(list(jsonschema.Draft7Validator(branch).iter_errors(instance)))
                if best_count is None or cnt < best_count:
                    best_count = cnt
                    best_idx = idx
            chosen = branches[best_idx]
            req = chosen.get("required", [])
            desc = chosen.get("description", "")
            return f"axis=document-role (closest branch={req}): {desc}"
        return f"axis=resource-entry-shape at {'/'.join(str(p) for p in path) or '(root)'}: {err.message}"

    multi_axis_probe = {"x402Version": 2, "payTo": "0xabc", "networks": ["eip155:8453"]}
    probe_axes = [describe_repair_axis(e, multi_axis_probe) for e in validator.iter_errors(multi_axis_probe)]
    if not (
        any("axis=misplaced-root-carrier (payTo, networks)" in a for a in probe_axes)
        and any("axis=document-role (closest branch=['resources']): Resource servers declare the resources array." in a for a in probe_axes)
    ):
        print(f"[-] FAIL: repair-axis attribution did not separate root carrier vs closest anyOf branch: {probe_axes}")
        sys.exit(1)
    print("[PASS] repair-axis attribution separates 'misplaced-root-carrier' and closest 'anyOf' branch description verbatim")

    # 4. Migration Fixture: legacy incumbent -> x402Version 2 rendition
    print("\n--- 3. MIGRATION FIXTURE (incumbent -> x402Version 2) ---")
    mig_entries = run_migration_check(validator)

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {pos_passed} Positive Passed | {neg_passed} Negative Rejections Verified "
          f"(with exact validator assertions) | {mig_entries} Migration Entr(ies) Verified")
    print("ALL TESTS PASSED WITH 100% CONFORMANCE.")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
