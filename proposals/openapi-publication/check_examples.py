"""Offline fixture proof and artifact generation; no network or payment calls."""
import argparse
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / 'examples'
TRAVEL_PATH = '/api/seats-aero/routes'
STUDIO_PATH = '/api/generate/nano-banana-pro/generate'


def read(name):
    return json.loads((EXAMPLES / name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def merge(target, update):
    for key, value in update.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            merge(target[key], value)
        elif key in target and isinstance(target[key], list) and isinstance(value, list):
            target[key].extend(copy.deepcopy(value))
        else:
            target[key] = copy.deepcopy(value)


def compose(base, overlay):
    result = copy.deepcopy(base)
    for action in overlay['actions']:
        selector = action['target']
        if not re.fullmatch(r"\$(\['[^']+'\])+", selector):
            raise ValueError('Only exact member selectors are supported')
        node = result
        for key in re.findall(r"\['([^']+)'\]", selector):
            if not isinstance(node, dict) or key not in node:
                raise ValueError('Overlay target absent: ' + selector)
            node = node[key]
        if not isinstance(node, dict) or set(action) != {'target', 'update'}:
            raise ValueError('Only object update actions are supported')
        merge(node, action['update'])
    return result


def check_refs(value, document):
    if isinstance(value, dict):
        if '$ref' in value:
            ref = value['$ref']
            require(ref.startswith('#/'), 'Example must include its referenced schemas')
            node = document
            for part in ref[2:].split('/'):
                node = node[part.replace('~1', '/').replace('~0', '~')]
        for child in value.values():
            check_refs(child, document)
    elif isinstance(value, list):
        for child in value:
            check_refs(child, document)


def check_price(annotation):
    if 'price' in annotation:
        price = annotation['price']
        require(Decimal(price['min']) <= Decimal(price['max']), 'Price min exceeds max')


def build():
    sources = {service: read(service + '.source.openapi.json')
               for service in ['stabletravel', 'stablestudio']}
    evidence = read('evidence.json')
    for service, document in sources.items():
        for path, methods in evidence['sources'][service]['operations'].items():
            for method, expected in methods.items():
                operation = document['paths'][path][method]
                encoded = json.dumps(operation, sort_keys=True, separators=(',', ':')).encode()
                require(hashlib.sha256(encoded).hexdigest() == expected,
                        'Captured source operation changed: ' + path)
        check_refs(document, document)
    challenge = read('stabletravel.challenge-excerpt.json')
    # Source-only conventions are evidence, not part of the proposed publication.
    clean = copy.deepcopy(sources)
    for document in clean.values():
        for item in document['paths'].values():
            for op in item.values():
                if isinstance(op, dict):
                    op.pop('x-payment-info', None)
    travel = copy.deepcopy(clean['stabletravel'])
    operation = travel['paths'][TRAVEL_PATH]['get']
    operation['description'] = challenge['resource']['description']
    source_price = sources['stabletravel']['paths'][TRAVEL_PATH]['get']['x-payment-info']['price']
    operation['x-x402'] = {
        'x402Version': 2,
        'price': {'currency': source_price['currency'], 'min': source_price['amount'], 'max': source_price['amount']},
        'accepts': [dict({key: option[key] for key in ['scheme', 'network', 'asset', 'payTo']},
                         payToType='address') for option in challenge['accepts']]}
    check_price(operation['x-x402'])
    operation['responses']['402']['headers'] = {'PAYMENT-REQUIRED': {
        'description': 'Base64-encoded x402 v2 PaymentRequired object. Obtain fresh request-specific terms before payment.',
        'schema': {'type': 'string'}}}
    overlay = read('stabletravel.overlay.json')
    require(compose(clean['stabletravel'], overlay) == travel,
            'Direct and overlay publication differ')
    require(operation['parameters'] == sources['stabletravel']['paths'][TRAVEL_PATH]['get']['parameters'],
            'Input contract changed')
    require(operation['responses']['200'] == sources['stabletravel']['paths'][TRAVEL_PATH]['get']['responses']['200'],
            'Output contract changed')
    require('x-payment-info' not in operation, 'Source convention leaked into publication')
    bad = copy.deepcopy(overlay)
    bad['actions'][0]['target'] = "$['paths']['/missing']['get']"
    try:
        compose(clean['stabletravel'], bad)
    except ValueError:
        pass
    else:
        raise ValueError('Missing target did not fail')
    studio = copy.deepcopy(clean['stablestudio'])
    source_price = sources['stablestudio']['paths'][STUDIO_PATH]['post']['x-payment-info']['price']
    studio['paths'][STUDIO_PATH]['post']['x-x402'] = {
        'x402Version': 2,
        'price': {key: source_price[key] for key in ['currency', 'min', 'max']}}
    studio['paths'][STUDIO_PATH]['post']['responses']['402']['headers'] = copy.deepcopy(
        operation['responses']['402']['headers'])
    check_price(studio['paths'][STUDIO_PATH]['post']['x-x402'])
    poll = studio['paths']['/api/jobs/{jobId}']['get']
    poll['parameters'] = [{'name': 'jobId', 'in': 'path', 'required': True,
                           'schema': {'type': 'string'}}]
    require('x-x402' not in poll and poll['security'] == [{'siwx': []}],
            'Polling authentication incorrectly changed to payment')
    require(studio['paths'][STUDIO_PATH]['post']['x-x402']['price'] ==
            {'currency': 'USD', 'min': '0', 'max': '10.00'},
            'Captured price range changed')
    for document in [travel, studio]:
        for item in document['paths'].values():
            for op in item.values():
                if isinstance(op, dict) and 'price' in op.get('x-x402', {}):
                    require('PAYMENT-REQUIRED' in op['responses']['402'].get('headers', {}),
                            'Paid example lacks payment challenge header documentation')
        require('x-payment-info' not in json.dumps(document), 'Source convention leaked into publication')
    check_price({'x402Version': 2})  # Omitted price is valid, not free.
    try:
        check_price({'price': {'min': '10', 'max': '1'}})
    except ValueError:
        pass
    else:
        raise ValueError('Inverted range accepted')
    return {'stabletravel': travel, 'stablestudio': studio}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Refresh tracked final examples and write publication artifacts to build/')
    args = parser.parse_args()
    for service, document in build().items():
        entry = read(service + '.well-known.json')
        origin = document['servers'][0]['url']
        require(entry == {'x402Version': 2, 'openapi': [origin + '/openapi.json']},
                'Incorrect Option A entry or URL')
        for item in document['paths'].values():
            for operation in item.values():
                if isinstance(operation, dict) and 'x-x402' in operation:
                    require(operation['x-x402']['x402Version'] == entry['x402Version'],
                            'Entry and operation protocol versions differ')
        check_refs(document, document)
        snapshot = EXAMPLES / (service + '.final.openapi.json')
        if args.write:
            snapshot.write_text(json.dumps(document, indent=2) + '\n')
        require(json.loads(snapshot.read_text()) == document,
                'Final example differs from generated output: ' + service)
        if service == 'stabletravel':
            proposal = (ROOT / 'proposal.md').read_text()
            inline = proposal.split('<!-- final-stabletravel:start -->', 1)[1].split(
                '<!-- final-stabletravel:end -->', 1)[0]
            require(json.loads(inline.split('```json\n', 1)[1].split('```', 1)[0]) == document,
                    'Proposal final OpenAPI differs from generated output')
        if args.write:
            destination = ROOT / 'build' / service
            (destination / '.well-known').mkdir(parents=True, exist_ok=True)
            for path, content in [(destination / 'openapi.json', document),
                                  (destination / '.well-known/x402.json', entry)]:
                path.write_text(json.dumps(content, indent=2) + '\n')
    print('PASS: source integrity, references, direct/overlay equivalence, preserved contracts, optional prices and ranges, no vendor fields, authentication, entry URLs, missing target')


if __name__ == '__main__':
    main()
