"""Build proposed publication fixtures from frozen public service descriptions.
No API invocation or payment. Python standard library only.
"""
import copy
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / 'sources'
EXAMPLES = ROOT / 'examples'
METHODS = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'}

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

SELECTIONS = {
    'stabletravel': [('/api/google-flights/search', 'get'), ('/api/google-flights/booking', 'get'), ('/api/seats-aero/trips/id', 'get')],
    'stablestudio': [('/api/generate/nano-banana-pro/generate', 'post'), ('/api/jobs/{jobId}', 'get')],
    'stableupload': [('/api/upload', 'post'), ('/api/uploads', 'get'), ('/api/download/:uploadId', 'get'), ('/api/site', 'post'), ('/api/site', 'put'), ('/api/site/activate', 'post')],
}

def main():
    evidence = []
    for service, selected in SELECTIONS.items():
        host = service + '.dev'
        source_path = SOURCES / (host + '-openapi.json')
        raw = source_path.read_bytes()
        source = json.loads(raw)
        doc = {k: copy.deepcopy(v) for k, v in source.items() if k not in {'paths', 'x-discovery'}}
        # Keep the examples small and avoid embedding the full usage guide.
        doc['info'].pop('x-guidance', None)
        doc['info']['title'] += ' proposed publication example'
        doc['info']['version'] = 'example-2026-09-19'
        doc['paths'] = {}
        changes = []
        for old_path, method in selected:
            op = copy.deepcopy(source['paths'][old_path][method])
            path = old_path
            if old_path == '/api/seats-aero/trips/id':
                path = '/api/seats-aero/trips/{id}'
                op['parameters'] = [{'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}]
                changes.append('Proposed route-template correction from /trips/id to /trips/{id}, with required string parameter; usage-guide evidence, not live route verification.')
            if old_path == '/api/download/:uploadId':
                path = '/api/download/{uploadId}'
                op['parameters'] = [{'name': 'uploadId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}]
                changes.append('Converted documented :uploadId notation to OpenAPI {uploadId}; added required string parameter.')
            if service == 'stablestudio' and method == 'get':
                op['parameters'] = [{'name': 'jobId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}]
                changes.append('Added missing required jobId path parameter.')
            if service == 'stableupload' and path == '/api/site':
                op['operationId'] = 'site_create' if method == 'post' else 'site_update'
                changes.append('Assigned unique operationId ' + op['operationId'] + ' to ' + method.upper() + ' /api/site.')
            paid = 'x-payment-info' in op
            op['x-payment'] = {'mode': 'required' if paid else 'none'}
            if paid:
                # Our provisional summary; preserve the original extension unchanged.
                op['x-payment']['protocols'] = [{'name': 'x402'}, {'name': 'mpp'}]
            else:
                # No new fee is based on the usage guide, not merely absent metadata.
                changes.append(method.upper() + ' ' + path + ': no-new-payment summary based on the service usage guide; SIWX security retained.')
            doc['paths'].setdefault(path, {})[method] = op
        if service == 'stablestudio':
            doc['paths']['/api/generate/nano-banana-pro/generate']['post']['responses']['200']['links'] = {
                'pollJob': {'operationId': 'jobs_status', 'parameters': {'jobId': '$response.body#/jobId'}}
            }
            changes.append('Added proposed OpenAPI link from generation jobId to jobs_status; runtime pollUrl still subject to client origin policy.')
        changes.append('Added provisional x-payment mode/protocol summaries; no x402 version or recipient inferred from incomplete native metadata.')
        write(EXAMPLES / service / 'final.openapi.json', doc)
        manifest = {'discoveryVersion': '0.1', 'apis': [{'id': service, 'url': f'https://{host}/discovery/releases/example-2026-09-19/openapi.json'}]}
        write(EXAMPLES / service / 'well-known.json', manifest)
        write(EXAMPLES / service / 'changes.json', {'status': 'proposed, not deployed or merchant-approved', 'source': f'https://{host}/openapi.json', 'changes': changes})
        evidence.append({'service': service, 'source': f'https://{host}/openapi.json', 'captured': '2026-09-19', 'sha256': hashlib.sha256(raw).hexdigest(), 'sourceOperations': sum(m in METHODS for pi in source['paths'].values() for m in pi), 'exampleOperations': len(selected)})

    # Controlled managed-provider scenario using the SAME StableTravel operation.
    # This is an illustration, not a claim about StableTravel's implementation.
    direct = json.loads((EXAMPLES / 'stabletravel' / 'final.openapi.json').read_text())
    path = '/api/google-flights/search'
    final = copy.deepcopy(direct)
    final['paths'] = {path: {'get': copy.deepcopy(direct['paths'][path]['get'])}}
    base = copy.deepcopy(final)
    operation = base['paths'][path]['get']
    additions = {k: operation.pop(k) for k in ['x-payment-info', 'x-payment']}
    additions['responses'] = {'402': operation['responses'].pop('402')}
    overlay = {'overlay': '1.1.0', 'info': {'title': 'Illustrative managed payment provider', 'version': 'example-2026-09-19'}, 'actions': [{'target': "$['paths']['/api/google-flights/search']['get']", 'update': additions}]}
    write(EXAMPLES / 'managed-provider' / 'base.openapi.json', base)
    write(EXAMPLES / 'managed-provider' / 'provider.overlay.json', overlay)
    write(EXAMPLES / 'managed-provider' / 'expected.openapi.json', final)
    write(ROOT / 'evidence.json', evidence)

if __name__ == '__main__':
    main()
