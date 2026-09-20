"""Targeted offline checks, NOT a full OpenAPI or Overlay conformance validator.
Supports the exact member-selection JSONPath used in these fixtures only.
"""
import copy
import json
import pathlib
import re
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
METHODS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace'}
results = []

def load(path):
    return json.loads((ROOT / path).read_text())

def operations(doc):
    return [(p, m, o) for p, item in doc['paths'].items() for m, o in item.items() if m in METHODS]

def check_doc(doc):
    errors = []
    ids = []
    for path, method, op in operations(doc):
        ids.append(op.get('operationId'))
        params = op.get('parameters', []) + doc['paths'][path].get('parameters', [])
        declared = {p['name'] for p in params if p.get('in') == 'path' and p.get('required') is True}
        if set(re.findall(r'{([^}]+)}', path)) != declared:
            errors.append('path-parameters:' + path)
        if re.search(r'/:[^/]+', path):
            errors.append('colon-path:' + path)
        payment = op.get('x-payment', {})
        if payment.get('mode') == 'none' and op.get('x-payment-info'):
            errors.append('payment-conflict:' + path)
        if not op.get('responses'):
            errors.append('responses:' + path)
        for requirement in op.get('security', doc.get('security', [])):
            for name in requirement:
                if name not in doc.get('components', {}).get('securitySchemes', {}):
                    errors.append('unknown-security:' + name)
    if None in ids or len(ids) != len(set(ids)):
        errors.append('operation-ids')
    return errors

def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        for k, v in b.items():
            a[k] = merge(a[k], v) if k in a else copy.deepcopy(v)
        return a
    if isinstance(a, list) and isinstance(b, list):
        return a + copy.deepcopy(b)
    return copy.deepcopy(b)

def compose(base, overlay):
    doc = copy.deepcopy(base)
    for action in overlay['actions']:
        target = action['target']
        parts = re.findall(r"\['([^']+)'\]", target)
        if target != '$' + ''.join("['" + p + "']" for p in parts):
            raise ValueError('unsupported JSONPath in this fixture runner')
        node = doc
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise ValueError('publication error: target does not match')
            node = node[part]
        merge(node, action['update'])
    return doc

def test(name, ok):
    results.append({'name': name, 'passed': bool(ok)})
    if not ok:
        raise AssertionError(name)

def main():
    for service in ['stabletravel', 'stablestudio', 'stableupload']:
        doc = load(f'examples/{service}/final.openapi.json')
        test(service + ' targeted structure', not check_doc(doc))
        manifest = load(f'examples/{service}/well-known.json')
        host = service + '.dev'
        test(service + ' same-origin manifest and servers', urlparse(manifest['apis'][0]['url']).netloc == host and all(urlparse(s['url']).netloc == host for s in doc['servers']))
        source = load(f'sources/{host}-openapi.json')
        original = {o['operationId']: o for p, m, o in operations(source) if o.get('x-payment-info')}
        test(service + ' native payment metadata preserved', all(o['x-payment-info'] == original[o['operationId'] if o['operationId'] != 'site_create' else 'site']['x-payment-info'] for p, m, o in operations(doc) if o.get('x-payment-info')))
    studio = load('examples/stablestudio/final.openapi.json')
    poll = studio['paths']['/api/jobs/{jobId}']['get']
    test('authentication-only 402 allowed with no new payment', poll['x-payment']['mode'] == 'none' and '402' in poll['responses'] and bool(poll['security']))
    link = studio['paths']['/api/generate/nano-banana-pro/generate']['post']['responses']['200']['links']['pollJob']
    test('async link resolves', link['operationId'] == poll['operationId'] and link['parameters']['jobId'] == '$response.body#/jobId')
    base = load('examples/managed-provider/base.openapi.json')
    overlay = load('examples/managed-provider/provider.overlay.json')
    expected = load('examples/managed-provider/expected.openapi.json')
    test('managed composition equals direct publication operation', compose(base, overlay) == expected)
    test('fresh-base rebuild preserves one protocol list', compose(base, overlay)['paths']['/api/google-flights/search']['get']['x-payment-info']['protocols'] == expected['paths']['/api/google-flights/search']['get']['x-payment-info']['protocols'] and 'x-payment-info' not in base['paths']['/api/google-flights/search']['get'])
    bad = copy.deepcopy(overlay)
    bad['actions'][0]['target'] = "$['paths']['/renamed']['get']"
    try:
        compose(base, bad)
        rejected = False
    except ValueError:
        rejected = True
    test('stale target rejected', rejected)
    bad = copy.deepcopy(expected)
    bad['paths']['/api/google-flights/search']['get']['x-payment']['mode'] = 'none'
    test('contradictory free claim rejected', bool(check_doc(bad)))
    upload = load('sources/stableupload.dev-openapi.json')
    test('source duplicate IDs detected', 'operation-ids' in check_doc(upload))
    test('source colon route detected', any(e.startswith('colon-path:') for e in check_doc(upload)))
    original_studio = load('sources/stablestudio.dev-openapi.json')
    test('source missing job parameter detected', any(e.startswith('path-parameters:') for e in check_doc(original_studio)))
    report = {'scope': 'Targeted offline fixture checks only; no runtime, payment, full OpenAPI validation, or full Overlay conformance claim.', 'checks': results}
    (ROOT / 'check-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(results)} targeted checks passed')

if __name__ == '__main__':
    main()
