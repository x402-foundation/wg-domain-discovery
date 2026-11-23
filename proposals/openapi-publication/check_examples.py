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


# Decimals of the USDC assets used in the captured challenges.
USDC_DECIMALS = {'0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913': 6,
                 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 6}


def atomic(price, asset):
    return str(int(Decimal(price) * 10 ** USDC_DECIMALS[asset]))


def check_amounts(annotation):
    for option in annotation.get('accepts', []):
        if 'minAmount' in option or 'maxAmount' in option:
            require({'minAmount', 'maxAmount', 'asset'} <= set(option),
                    'Amount bounds require minAmount, maxAmount and asset')
            require(int(option['minAmount']) <= int(option['maxAmount']), 'minAmount exceeds maxAmount')


def option_summary(option, low, high):
    return {'scheme': option['scheme'], 'network': option['network'], 'asset': option['asset'],
            'minAmount': low, 'maxAmount': high}


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
    operation['description'] = challenge['resource']['description'] + ' Charged per request.'
    source_price = sources['stabletravel']['paths'][TRAVEL_PATH]['get']['x-payment-info']['price']
    require(source_price['currency'] == 'USD', 'StableTravel price is no longer in USD')
    for option in challenge['accepts']:
        # The documented USD price and the live USDC amount must agree.
        require(atomic(source_price['amount'], option['asset']) == option['amount'],
                'Documented price and live amount differ')
    operation['x-x402'] = {'accepts': [option_summary(option, option['amount'], option['amount'])
                                       for option in challenge['accepts']]}
    check_amounts(operation['x-x402'])
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
    generate = studio['paths'][STUDIO_PATH]['post']
    generate['description'] = (
        'Generate an image with Nano Banana Pro. Returns an asynchronous job; poll its pollUrl with SIWX '
        'until the job is complete or failed. The price is dynamic within the advertised range; '
        'the live challenge gives the exact amount for the request.')
    generate['responses']['200']['links'] = {'pollJob': {
        'operationId': 'jobs_status', 'parameters': {'jobId': '$response.body#/jobId'}}}
    studio['components']['securitySchemes']['siwx']['description'] = (
        'Base64-encoded SIWX proof obtained by signing a fresh server challenge.')
    require({key: source_price[key] for key in ['currency', 'min', 'max']} ==
            {'currency': 'USD', 'min': '0', 'max': '10.00'}, 'Captured price range changed')
    studio_challenge = read('stablestudio.challenge-excerpt.json')
    generate['x-x402'] = {'accepts': [
        option_summary(option, atomic(source_price['min'], option['asset']),
                       atomic(source_price['max'], option['asset']))
        for option in studio_challenge['accepts']]}
    check_amounts(generate['x-x402'])
    for option, summary in zip(studio_challenge['accepts'], generate['x-x402']['accepts']):
        require(int(summary['minAmount']) <= int(option['amount']) <= int(summary['maxAmount']),
                'Live amount outside the advertised range')
    generate['responses']['402']['headers'] = copy.deepcopy(operation['responses']['402']['headers'])
    poll = studio['paths']['/api/jobs/{jobId}']['get']
    poll['parameters'] = [{'name': 'jobId', 'in': 'path', 'required': True,
                           'schema': {'type': 'string'}}]
    poll['x-x402'] = {'extensions': {'sign-in-with-x': {}}}
    require(poll['security'] == [{'siwx': []}] and 'accepts' not in poll['x-x402'],
            'Polling authentication incorrectly changed to payment')
    require(any(op.get('operationId') == 'jobs_status'
                for item in studio['paths'].values() for op in item.values() if isinstance(op, dict)),
            'Generate link targets a missing operation')
    for document in [travel, studio]:
        for item in document['paths'].values():
            for op in item.values():
                if isinstance(op, dict) and 'accepts' in op.get('x-x402', {}):
                    require('PAYMENT-REQUIRED' in op['responses']['402'].get('headers', {}),
                            'Paid example lacks payment challenge header documentation')
        require('x-payment-info' not in json.dumps(document), 'Source convention leaked into publication')
    check_amounts({})  # Omitted amounts are valid, not free.
    for bad_option in [{'minAmount': '10', 'maxAmount': '1', 'asset': 'USD'}, {'minAmount': '1', 'asset': 'USD'}]:
        try:
            check_amounts({'accepts': [dict(bad_option, scheme='exact', network='eip155:8453')]})
        except ValueError:
            continue
        raise ValueError('Invalid amount bounds accepted')
    return {'stabletravel': travel, 'stablestudio': studio}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Refresh tracked final examples and write publication artifacts to build/')
    args = parser.parse_args()
    for service, document in build().items():
        entry = read(service + '.well-known.json')
        origin = document['servers'][0]['url']
        require(entry == {'x402Version': 2, 'openapi': [origin + '/openapi.json']},
                'Incorrect entry or URL')
        for item in document['paths'].values():
            for operation in item.values():
                if isinstance(operation, dict) and 'x-x402' in operation:
                    # The entry carries the protocol version; operations do not repeat it.
                    require('x402Version' not in operation['x-x402'], 'Operation repeats the entry version')
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
                                  (destination / '.well-known/x402', entry)]:
                path.write_text(json.dumps(content, indent=2) + '\n')
    print('PASS: source integrity, references, direct/overlay equivalence, preserved contracts, documented and live amounts agree, optional amount ranges, no vendor fields, authentication, entry URLs, missing target')


if __name__ == '__main__':
    main()
