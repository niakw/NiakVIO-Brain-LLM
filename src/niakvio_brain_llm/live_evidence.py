"""Bound live diagnostics to structural facts, never response scalar values."""
import json
import re
import ipaddress
from urllib.parse import urlsplit
from .source_units import javascript_function_end

IDENTIFIER = re.compile(r"[A-Za-z_$][\w$-]{0,47}")
SENSITIVE = re.compile(r"key|token|auth|signature|secret|password|cookie|session|nonce", re.I)
ADDRESS_SCOPE = re.compile(r"s[0-9a-f]{16}")
ADDRESS_REF = re.compile(r"r(?:[1-9]|[1-9][0-9]|[1-4][0-9]{2}|50[0-9]|51[0-2])")
NETWORK_ERROR_CODES = frozenset({
    'ENOTFOUND', 'EAI_AGAIN', 'ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT',
    'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_SOCKET',
    'CERT_HAS_EXPIRED', 'ERR_TLS_CERT_ALTNAME_INVALID', 'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    'DEPTH_ZERO_SELF_SIGNED_CERT', 'NUVIO_FETCH_TIMEOUT',
})


def public_domain_references(values):
    """Validate immutable public-source candidates, without granting proof."""
    result = []
    for row in rows(values, 12):
        if not isinstance(row, dict):
            continue
        origin, source, sha = (row.get(key) for key in ('origin', 'source_url', 'source_sha'))
        if (not all(isinstance(value, str) for value in (origin, source, sha))
                or not re.fullmatch(r'[0-9a-f]{40}', sha)
                or len(origin) > 253 or len(source) > 600
                or any(re.search(r'[\x00-\x20\x7f\\]', value) for value in (origin, source))):
            continue
        try:
            site, reference = urlsplit(origin), urlsplit(source)
            host = site.hostname or ''
            if (site.scheme != 'https' or site.username or site.password or site.port
                    or site.path or site.query or site.fragment
                    or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', host)
                    or host.endswith(('.localhost', '.local', '.internal', '.invalid', '.example', '.test'))):
                continue
            try:
                ipaddress.ip_address(host)
                continue
            except ValueError:
                pass
            if (reference.scheme != 'https' or reference.username or reference.password
                    or reference.port or reference.query or reference.fragment):
                continue
            prefix = r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/'
            suffix = re.escape(sha) + r'/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+'
            pattern = prefix + ('blob/' if reference.hostname == 'github.com' else '') + suffix
            if (reference.hostname not in {'github.com', 'raw.githubusercontent.com'}
                    or not re.fullmatch(pattern, reference.path)
                    or any(part in {'.', '..'} for part in reference.path.split('/'))):
                continue
        except ValueError:
            continue
        item = {'origin': 'https://' + host, 'source_url': source, 'source_sha': sha}
        if item not in result:
            result.append(item)
        if len(result) == 3:
            break
    return result


def domain_reference_focus(live):
    """404-only failed fixtures justify a domain-data hypothesis, not success."""
    live = live if isinstance(live, dict) else {}
    references = public_domain_references(live.get('public_domain_references'))
    failed = {row['fixture'] for row in fixture_evidence(live.get('fixture_evidence'))
              if row['streamsReturned'] == 0 and row['streamsPlayable'] == 0}
    events = [row for row in network_evidence(live.get('network_evidence'))
              if row['fixture'] in failed]
    return {'references': references, 'fixtures': sorted(failed)} \
        if references and events and all(row['status'] == 404 for row in events) else {}


def prioritize_domain_data(scopes, allowed, context):
    if ('provider_data' in allowed and context.get('override')
            and domain_reference_focus(context.get('live_runtime_evidence'))):
        return ['provider_data'] + [scope for scope in scopes if scope != 'provider_data']
    return scopes


def verified_live_failure(request):
    """A request-local preflight receipt permits synthesis, never publication."""
    proof = (request.provider_context or {}).get('verified_live_failure')
    if not isinstance(proof, dict) or proof.get('provider') != request.provider_id:
        return False
    if (not isinstance(proof.get('sourceSha'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', proof['sourceSha'])
            or proof.get('sourceValidated') is not True or proof.get('httpStatuses') != [404]
            or proof.get('publicationAuthority') is not False):
        return False
    failures = proof.get('fixtureFailures')
    return bool(isinstance(failures, list) and 0 < len(failures) <= 8 and all(
        isinstance(row, dict) and isinstance(row.get('fixture'), str) and row['fixture'].strip()
        and len(row['fixture']) <= 120 and not re.search(r'[\x00-\x1f\x7f]', row['fixture'])
        and type(row.get('streamsReturned')) is int and row['streamsReturned'] == 0
        and type(row.get('streamsPlayable')) is int and row['streamsPlayable'] == 0
        for row in failures))


def apply_verified_live_failure(request, live, source_sha, explicit_providers):
    """Demote stale positive priors only after the CLI verifies exact checkout evidence."""
    if (not isinstance(live, dict) or not isinstance(source_sha, str)
            or not re.fullmatch(r'[0-9a-f]{40}', source_sha)
            or live.get('sourceSha') != source_sha or live.get('provider') != request.provider_id
            or request.provider_id not in set(explicit_providers or [])
            or ' '.join(str(request.status).upper().replace('_', ' ').replace('-', ' ').split())
                not in {'FULL OK', 'PARTIAL OK'}):
        return False
    fixtures = live.get('fixture_evidence')
    if not isinstance(fixtures, list) or not 0 < len(fixtures) <= 8:
        return False
    failed, labels = [], set()
    for row in fixtures:
        if not isinstance(row, dict):
            return False
        label, returned, playable = row.get('fixture'), row.get('streamsReturned'), row.get('streamsPlayable')
        if (not isinstance(label, str) or not label.strip() or len(label) > 120
                or re.search(r'[\x00-\x1f\x7f]', label) or label in labels
                or type(returned) is not int or type(playable) is not int
                or not 0 <= playable <= returned):
            return False
        labels.add(label)
        if 'decodedMediaControls' in row and (type(row['decodedMediaControls']) is not int
                or not 0 <= row['decodedMediaControls'] <= playable):
            return False
        if returned == playable == 0:
            failed.append({'fixture': label, 'streamsReturned': 0, 'streamsPlayable': 0})
    if not failed:
        return False
    names = {row['fixture'] for row in failed}
    events = [row for row in rows(live.get('network_evidence'), 64)
              if isinstance(row, dict) and row.get('fixture') in names and not row.get('infrastructure')]
    if not events or any(type(row.get('status')) is not int or row['status'] != 404 for row in events):
        return False
    # Every failed fixture needs its own executed HTTP counterexample.
    if {row['fixture'] for row in events} != names:
        return False
    proof = {'provider': request.provider_id, 'sourceSha': source_sha, 'sourceValidated': True,
             'fixtureFailures': failed, 'httpStatuses': [404], 'publicationAuthority': False}
    previous_status, previous_failure = request.status, request.failure_class
    request.provider_context['verified_live_failure'] = proof
    request.status = 'CURRENT FAILURE'
    request.failure_class = 'provider_transport_gap'
    request.observations.insert(0, {'source': 'verified-live-preflight', 'stage': 'current_failure',
        'value': {**proof, 'historicalStatus': previous_status, 'historicalFailureClass': previous_failure},
        'instruction': 'Exact-current failed fixtures supersede a historical positive census for this attempt only. '
                       'This permits a provider-local proposal, not proof of a repair.'})
    return True


def address_scope(value):
    return isinstance(value, str) and ADDRESS_SCOPE.fullmatch(value) is not None


def address_ref(value):
    return isinstance(value, str) and ADDRESS_REF.fullmatch(value) is not None


def address_fields(value):
    """Opaque labels only have meaning inside their strictly validated scope."""
    if not address_scope(value.get('address_scope')):
        return {}
    result = {'address_scope': value['address_scope']}
    for name in ('address_refs_truncated', 'address_trace_truncated'):
        if name in value:
            result[name] = value[name] if type(value[name]) is bool else True
    for name in ('request_ref', 'response_ref', 'referer_ref'):
        if name in value:
            if address_ref(value[name]):
                result[name] = value[name]
            elif value[name] is not None and value[name] != '':
                result['address_refs_truncated'] = True
    return result


def markup_address_fields(value, attributes):
    result = {}
    if 'address_refs_truncated' in value:
        flag = value['address_refs_truncated']
        result['address_refs_truncated'] = flag if type(flag) is bool else True
    if 'address_refs' not in value:
        return result
    raw = value['address_refs']
    if not isinstance(raw, dict):
        result['address_refs_truncated'] = True
        return result
    projected = {}
    for attribute, refs in raw.items():
        if attribute not in attributes or not isinstance(refs, list):
            result['address_refs_truncated'] = True
            continue
        unique = []
        for ref in refs:
            if not address_ref(ref):
                result['address_refs_truncated'] = True
            elif ref not in unique:
                if len(unique) < 16:
                    unique.append(ref)
                else:
                    result['address_refs_truncated'] = True
        projected[attribute] = unique
    result['address_refs'] = projected
    return result


def rows(value, limit):
    return value[:limit] if isinstance(value, list) else []


def count(value, maximum=100000):
    return max(0, min(maximum, value)) if type(value) is int else 0


def identifiers(values, limit=16):
    return [name for name in values if isinstance(name, str) and IDENTIFIER.fullmatch(name)
            and not SENSITIVE.search(name)][:limit] if isinstance(values, list) else []


def player_markup(value, allow_address_refs=False):
    if not isinstance(value, dict):
        return {}
    attributes = {'src', 'data-src', 'href', 'value', 'data-url', 'data-link', 'data-player',
                  'data-embed', 'data-video', 'data-code', 'data-iframe', 'data-source',
                  'data-player-id', 'data-index', 'data-server'}
    kinds = {'empty', 'absolute_url', 'relative_url', 'fragment', 'inline_markup',
             'escaped_markup', 'encoded_markup', 'encoded_url', 'other'}
    shapes = {'image_extension', 'script_extension', 'style_extension', 'media_extension',
              'embed_route', 'page_extension', 'other', 'unknown'}
    origins = {'same_origin', 'cross_origin', 'unknown'}
    result = []
    refs_truncated = False
    raw_rows = value.get('rows') if isinstance(value.get('rows'), list) else []
    for index, row in enumerate(raw_rows):
        row_has_refs = (allow_address_refs and isinstance(row, dict)
                        and any(key in row for key in ('address_refs', 'address_refs_truncated')))
        if index >= 8:
            refs_truncated = refs_truncated or row_has_refs
            continue
        if not isinstance(row, dict) or row.get('tag') not in {
            'iframe', 'video', 'source', 'a', 'button', 'option', 'div', 'li', 'input'
        }:
            refs_truncated = refs_truncated or row_has_refs
            continue
        raw = row.get('value_kinds')
        projected = {name: kind for name, kind in raw.items()
                     if name in attributes and isinstance(kind, str) and kind in kinds} if isinstance(raw, dict) else {}
        projected = dict(list(projected.items())[:8])
        if projected:
            total = count(row.get('count'), 128)
            item = {'tag': row['tag'], 'value_kinds': projected, 'count': total,
                    'distinct_values': min(total, count(row.get('distinct_values'), 128))}
            if allow_address_refs:
                item.update(markup_address_fields(row, projected))
                refs_truncated = refs_truncated or item.get('address_refs_truncated') is True
            raw_shapes = row.get('value_shapes')
            if isinstance(raw_shapes, dict):
                classified = {}
                for attribute in projected:
                    shape = raw_shapes.get(attribute)
                    if (isinstance(shape, dict) and isinstance(shape.get('kind'), str)
                            and shape['kind'] in shapes and isinstance(shape.get('origin'), str)
                            and shape['origin'] in origins):
                        classified[attribute] = {'kind': shape['kind'], 'origin': shape['origin']}
                if classified:
                    item['value_shapes'] = classified
            result.append(item)
        elif row_has_refs:
            refs_truncated = True
    return {'rows': result, 'sampled_chars': count(value.get('sampled_chars'), 131072),
            'truncated': value.get('truncated') is True or refs_truncated}


def response_structure(value, allow_address_refs=False):
    if not isinstance(value, dict):
        return {}
    kind = value.get("kind")
    if kind == "json":
        fields = []
        for row in rows(value.get("fields"), 16):
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "")[:160]
            parts = path.replace("[]", "").split(".")
            if not all(IDENTIFIER.fullmatch(part) and not SENSITIVE.search(part) for part in parts):
                continue
            if row.get("type") in {"string", "number", "boolean", "null", "object", "array"}:
                fields.append({"path": path, "type": row["type"]})
        result = {"kind": kind, "fields": fields}
        raw = value.get("graphql")
        if isinstance(raw, dict):
            # Only bounded enum facts from the deterministic response classifier
            # enter Brain. Never admit arbitrary GraphQL error messages/values.
            valid_codes = {
                "GRAPHQL_VALIDATION_FAILED", "GRAPHQL_PARSE_FAILED",
                "BAD_USER_INPUT", "BAD_REQUEST", "UNAUTHENTICATED",
                "FORBIDDEN", "INTERNAL_SERVER_ERROR", "SERVICE_UNAVAILABLE",
                "PERSISTED_QUERY_NOT_FOUND", "TOO_MANY_REQUESTS", "NOT_FOUND",
            }
            valid_kinds = {
                "schema_mismatch", "syntax", "auth", "rate_limit",
                "timeout", "not_found", "server_error", "unknown",
            }
            states = {"missing", "null", "object", "array", "scalar"}
            null_fields = {
                "episode", "shows", "sources", "search", "media",
                "video", "results", "title",
            }
            result["graphql"] = {
                "errorCount": count(raw.get("errorCount"), 16),
                "codes": list(dict.fromkeys(
                    x for x in rows(raw.get("codes"), 8)
                    if isinstance(x, str) and x in valid_codes
                ))[:8],
                "kinds": list(dict.fromkeys(
                    x for x in rows(raw.get("kinds"), 8)
                    if isinstance(x, str) and x in valid_kinds
                ))[:8],
                "dataState": raw["dataState"] if isinstance(raw.get("dataState"), str)
                    and raw["dataState"] in states else "missing",
                "nullRoots": list(dict.fromkeys(
                    x for x in rows(raw.get("nullRoots"), 8)
                    if isinstance(x, str) and x in null_fields
                ))[:8],
            }
        return result
    if kind == "html":
        result = {"kind": kind, "tags": [
            {"tag": row["tag"], "attributes": identifiers(row.get("attributes"))}
            for row in rows(value.get("tags"), 8) if isinstance(row, dict)
            and row.get("tag") in {"iframe", "script", "video", "source", "a", "button", "select", "option"}
        ], "variables": identifiers(value.get("variables"))}
        if isinstance(value.get('player_markup'), dict):
            result['player_markup'] = player_markup(value['player_markup'], allow_address_refs)
        if isinstance(value.get('inline_fields'), list):
            result['inline_fields'] = [
                {'name': row['name'], 'type': row['type'], 'key_syntax': row['key_syntax']}
                for row in rows(value['inline_fields'], 12) if isinstance(row, dict)
                and isinstance(row.get('name'), str) and IDENTIFIER.fullmatch(row['name'])
                and not SENSITIVE.search(row['name'])
                and isinstance(row.get('type'), str) and row['type'] in
                    {'string', 'number', 'boolean', 'null', 'object', 'array'}
                and isinstance(row.get('key_syntax'), str) and row['key_syntax'] in {'quoted', 'bare'}]
        if isinstance(value.get('script_resources'), list):
            kinds = {'absolute_url', 'protocol_relative_url', 'root_relative_url', 'relative_path'}
            roles = {'app_entry', 'start_entry', 'chunk', 'other_script'}
            locations = {'src_attribute', 'inline_import'}
            result['script_resources'] = [
                {key: row[key] for key in ('kind', 'role', 'location')}
                for row in rows(value['script_resources'], 8) if isinstance(row, dict)
                and isinstance(row.get('kind'), str) and row['kind'] in kinds
                and isinstance(row.get('role'), str) and row['role'] in roles
                and isinstance(row.get('location'), str) and row['location'] in locations]
        return result
    return {"kind": kind} if kind in {"text", "binary"} else {}


def network_evidence(values):
    result, selection_structures = [], []
    for row in rows(values, 12):
        if not isinstance(row, dict):
            continue
        host = str(row.get("host") or "").lower()
        stage = str(row.get("stage") or "")
        status = row.get("status")
        item = {
            "fixture": re.sub(r'[\x00-\x1f\x7f]', '', str(row.get('fixture') or ''))[:120],
            "host": host if re.fullmatch(r"[a-z0-9.-]{1,160}", host) else "",
            "stage": stage if re.fullmatch(r"[a-z_]{1,40}", stage) else "",
            "status": status if type(status) is int and 100 <= status <= 599 else None,
            "functions": identifiers(row.get("functions"), 8),
            "response_structure": response_structure(row.get("response_structure"),
                                                      address_scope(row.get('address_scope'))),
            "announced_players": count(row.get("announced_players"), 256),
        }
        item.update(address_fields(row))
        if isinstance(row.get('error_code'), str) and row['error_code'] in NETWORK_ERROR_CODES:
            item['error_code'] = row['error_code']
        media = row.get('media_observation')
        if isinstance(row.get('http_observation'), dict):
            item['http_observation'] = http_observation(row['http_observation'])
        if isinstance(row.get('reader_user_agent_probe'), dict) and row['reader_user_agent_probe']:
            item['reader_user_agent_probe'] = reader_user_agent_probe(row['reader_user_agent_probe'])
        if 'address_scope' in item:
            probe = observed_media_probe(row.get('observed_media_probe'))
            if probe is not None:
                item['observed_media_probe'] = probe
        if isinstance(media, dict):
            item['media_observation'] = media_observation(media)
        result.append(item)
        # A ref loss may set markup.truncated, but that diagnostic must not
        # create a new structural alternative in the existing event selection.
        selection_structures.append(response_structure(row.get('response_structure'))
                                    if 'address_scope' in item else item['response_structure'])
    omitted_scopes = {row['address_scope'] for row in values[12:]
                      if isinstance(row, dict) and address_scope(row.get('address_scope'))} \
        if isinstance(values, list) else set()
    if len(result) <= 8:
        for item in result:
            if item.get('address_scope') in omitted_scopes:
                item['address_trace_truncated'] = True
        return result
    # Repeated player replies must not hide the episode/lookup context. Reserve
    # one event per fixture/stage, then retain distinct shapes before duplicates.
    primary, alternatives, duplicates = [], [], []
    phases, shapes = set(), set()
    for item, structural in zip(result, selection_structures):
        # Opaque correlation labels must not change the existing preference for
        # distinct structural evidence over repeated player replies.
        shape = {key: value for key, value in item.items() if key not in {
            'address_scope', 'request_ref', 'response_ref', 'referer_ref',
            'address_refs_truncated', 'address_trace_truncated', 'observed_media_probe'}}
        structure = dict(structural)
        if 'player_markup' in structure:
            structure['player_markup'] = {key: value for key, value in structure['player_markup'].items()
                                          if key != 'sampled_chars'}
        shape['response_structure'] = structure
        key = json.dumps(shape, sort_keys=True)
        phase = (item['fixture'], item['stage'])
        if phase not in phases:
            primary.append(item)
            phases.add(phase)
        elif key not in shapes:
            alternatives.append(item)
        else:
            duplicates.append(item)
        shapes.add(key)
    # The bounded control may be attached to a repeated reader response. Keep
    # its parent event after phase coverage, before ordinary alternatives, so
    # a real late control result survives this smaller prompt window.
    controls = [item for item in alternatives + duplicates if 'observed_media_probe' in item]
    ranked = primary + controls + [item for item in alternatives + duplicates
                                  if 'observed_media_probe' not in item]
    selected = ranked[:8]
    omitted_scopes.update(item['address_scope'] for item in ranked[8:] if 'address_scope' in item)
    for item in selected:
        if item.get('address_scope') in omitted_scopes:
            item['address_trace_truncated'] = True
    return selected


def http_observation(value):
    """Error-page signals are bounded syntax clues, never playback proof."""
    enums = {
        'content_kind': {'html', 'json', 'text', 'media', 'binary', 'unknown'},
        'url_relation': {'same_url', 'same_origin', 'cross_origin', 'unknown'},
        'body_state': {'not_sampled', 'sampled', 'complete', 'empty', 'timeout', 'error', 'unavailable'},
        'page_signal': {'challenge_markup', 'captcha_markup', 'access_denied_text',
                        'not_found_text', 'rate_limit_text', 'none', 'unknown'},
    }
    result = {key: value[key] if isinstance(value.get(key), str) and value[key] in allowed
              else 'unknown' if 'unknown' in allowed else 'unavailable'
              for key, allowed in enums.items()}
    result['sampled_bytes'] = count(value.get('sampled_bytes'), 8192)
    return result


def media_observation(value, prefix_limit=65536):
    enums = {
        'signature': ({'unknown', 'mp4', 'ebml', 'mpegts', 'hls', 'html'}, 'unknown'),
        'readState': ({'not_read', 'data', 'empty', 'complete', 'error'}, 'not_read'),
        'cancelState': ({'not_requested', 'requested', 'complete', 'error'}, 'not_requested'),
    }
    result = {key: value[key] if isinstance(value.get(key), str) and value[key] in allowed else default
              for key, (allowed, default) in enums.items()}
    result['durationSeconds'] = count(value.get('durationSeconds'), 1209600) \
        if type(value.get('durationSeconds')) is int else None
    result['bytesSampled'] = count(value.get('bytesSampled'), prefix_limit)
    return result


def observed_media_probe(value):
    """A bounded control request is diagnostic evidence, never a stream verdict."""
    if (not isinstance(value, dict) or type(value.get('attempted')) is not bool
            or not address_ref(value.get('source_ref')) or not address_ref(value.get('template_ref'))):
        return None
    attempted, outcome = value['attempted'], value.get('outcome')
    if not attempted and outcome != 'budget_exhausted':
        return None
    if attempted and (not isinstance(outcome, str) or outcome not in {'response', 'timeout', 'error'}):
        outcome = 'error'
    status = value.get('status')
    media, http = value.get('media_observation'), value.get('http_observation')
    return {
        'attempted': attempted, 'source_ref': value['source_ref'], 'template_ref': value['template_ref'],
        'status': status if attempted and outcome == 'response' and type(status) is int and 100 <= status <= 599 else None,
        'outcome': outcome,
        'media_observation': media_observation(media if isinstance(media, dict) else {}, 32768),
        'http_observation': http_observation(http if isinstance(http, dict) else {}),
    }


def reader_user_agent_probe(value):
    """Preserve a controlled diagnostic result without retaining its inputs."""
    attempted = value.get('attempted') is True
    outcome = value.get('outcome')
    if attempted:
        outcome = outcome if isinstance(outcome, str) and outcome in {'response', 'timeout', 'error'} else 'error'
    else:
        outcome = 'budget_exhausted' if outcome == 'budget_exhausted' else 'missing_profile'
    status = value.get('status')
    http = value.get('http_observation')
    return {
        'attempted': attempted, 'profile_source': 'prior_successful_html', 'changed_header': 'user-agent',
        'status': status if attempted and outcome == 'response' and type(status) is int and 100 <= status <= 599 else None,
        'outcome': outcome, 'http_observation': http_observation(http if isinstance(http, dict) else {}),
    }


def fixture_evidence(values):
    result = [{
        'fixture': re.sub(r'[\x00-\x1f\x7f]', '', str(row.get('fixture') or ''))[:120],
        'category': row.get('category') if row.get('category') in {'movie', 'tv', 'anime'} else '',
        'status': re.sub(r'[^a-z_]', '', str(row.get('status') or ''))[:64],
        'streamsPlayable': count(row.get('streamsPlayable')),
        'streamsReturned': count(row.get('streamsReturned')),
    } for row in rows(values, 8) if isinstance(row, dict)]
    for output, row in zip(result, [row for row in rows(values, 8) if isinstance(row, dict)]):
        if type(row.get('expectedDurationSeconds')) is int and 0 < row['expectedDurationSeconds'] <= 1209600:
            output['expectedDurationSeconds'] = row['expectedDurationSeconds']
        if 'decodedMediaControls' in row:
            output['decodedMediaControls'] = count(row.get('decodedMediaControls'), 8)
    return result


def verification_feedback(value):
    if not isinstance(value, dict) or not value:
        return {}
    result = {"reason": re.sub(r"[^a-zA-Z0-9._:-]", "_", str(value.get("reason") or ""))[:160]}
    result['executionObserved'] = value.get('executionObserved') is True
    result['materializedMutationObserved'] = value.get('materializedMutationObserved') is True
    for phase in ("baseline", "candidate"):
        row = value.get(phase) if isinstance(value.get(phase), dict) else {}
        result[phase] = {key: count(row.get(key))
                         for key in ("streamsPlayable", "streamsReturned", "identityContradictions")}
        result[phase]['fixtureCoverage'] = fixture_evidence(row.get('fixtureCoverage'))
        # Keep numeric fanout progress in the negative-memory feedback. A repair
        # with no decoded media may still open new player/variant branches, so
        # that attempt must not blacklist its edit locality as ineffective.
        coverage = row.get('variantCoverage') if isinstance(row.get('variantCoverage'), dict) else {}
        result[phase]['variantCoverage'] = {
            key: count(coverage.get(key))
            for key in ('announcedPlayerCandidates', 'announcedVariantCandidates',
                        'exploredPlayerRequests', 'maxPlayableHeight')
        }
    result["candidate_network"] = network_evidence(value.get("candidate_network"))
    return result


def _short_media_fixtures(live, observations):
    """Same-fixture evidence of a completely observed short terminal prefix."""
    expected = {row['fixture']: row['expectedDurationSeconds']
                for row in fixture_evidence(live.get('fixture_evidence'))
                if row['streamsReturned'] == 0 and row.get('expectedDurationSeconds', 0) >= 600}
    failed = {}
    for row in observations:
        media = row.get('media_observation') or {}
        duration = media.get('durationSeconds')
        if (row['fixture'] in expected and row['status'] in {200, 206}
                and media.get('signature') == 'mp4' and type(duration) is int and 0 < duration < 60
                and media.get('bytesSampled', 0) >= 40 and media.get('readState') in {'data', 'complete'}
                and (media.get('cancelState') == 'complete' or media.get('readState') == 'complete')):
            failed[row['fixture']] = duration
    return [{'fixture': name, 'sampledDurationSeconds': duration,
             'expectedDurationSeconds': expected[name]} for name, duration in failed.items()]


def short_media_source_focus(source, live):
    """Choose edit surfaces from short media evidence without changing acceptance."""
    observations = network_evidence(live.get('network_evidence'))
    fixtures = _short_media_fixtures(live, observations)
    failed = {row['fixture'] for row in fixtures}
    if not failed:
        return {}
    source = str(source or '')
    for marker in ('/* STARTFIX:CORE.', '/* NUVIO_GLOBAL_CORE_START_BOUNDARY_V1 */'):
        source = source.split(marker, 1)[0]
    functions = {}
    for match in re.finditer(r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', source):
        end = javascript_function_end(source, match.start())
        if end is not None and end > match.start():
            functions.setdefault(match.group(1), source[match.start():end])
    terminal = []
    for row in observations:
        tags = {tag.get('tag') for tag in (row.get('response_structure') or {}).get('tags', [])}
        if row['fixture'] not in failed or not tags.intersection({'video', 'source'}):
            continue
        for name in row['functions']:
            if (name in functions and not re.search(r'fetch|request', name, re.I)
                    and name not in {'text', 'json', 'wrapped', 'wrap', 'apiJson', 'jsonPostAt'}):
                if name not in terminal:
                    terminal.append(name)
                break
    if not terminal:
        return {}
    foreign_reader_pages = any(
        row['fixture'] in failed and row['stage'] == 'player' and row['status'] in {200, 206}
        and any(markup['tag'] == 'iframe' and any(
            shape['kind'] == 'page_extension' and shape['origin'] == 'cross_origin'
            for attribute, shape in markup.get('value_shapes', {}).items() if attribute in {'src', 'data-src'}
        ) for markup in (row.get('response_structure') or {}).get('player_markup', {}).get('rows', []))
        for row in observations
    )
    if foreign_reader_pages and non_improving_functions(source, live):
        # A crawler can reject a declared reader before any request is visible.
        # Offer named seed-admission callbacks, not its media/identity validators.
        protected = re.compile(r'identity|validat|incomplete|probe|verify|directmedia', re.I)
        admission = []
        for terminal_name in terminal:
            body = functions[terminal_name]
            boundary = re.search(r'\b(?:while|for)\s*\(|\bawait\b', body)
            setup = body[:boundary.start()] if boundary else body
            for name in re.findall(r'\.filter\s*\(\s*([A-Za-z_$][\w$]*)\s*\)', setup):
                if name not in functions or protected.search(name) or name in admission:
                    continue
                admission.append(name)
                for callee in re.findall(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(', functions[name]):
                    target = functions.get(callee, '')
                    if (callee not in admission and not protected.search(callee)
                            and re.search(r'new\s+URL\s*\(|\.pathname\b|\.searchParams\b', target)):
                        admission.append(callee)
                if admission:
                    break
            if admission:
                break
        if admission:
            return {'reason': 'declared_reader_seed_admission', 'selector_functions': admission[:3],
                    'seed_admission_functions': admission[:3], 'terminal_functions': terminal[:2],
                    'fixtures': fixtures[:4],
                    'policy': 'URL admission only; preserve protocol, asset, incomplete-identity, media and identity checks. '
                              'An executed reader HTTP failure means admission reached that reader. '
                              'Inspect previous_verification.candidate_network HTTP observations before another admission edit; '
                              'page signals are diagnostic clues, not proof of a working source. '
                              'Abstain if the offered functions cannot causally address the observed failure.'}
    selectors = []
    for parent in identifiers(live.get('active_functions'), 6):
        body = functions.get(parent, '')
        if parent in terminal or not any(re.search(r'\b' + re.escape(name) + r'\s*\(', body) for name in terminal):
            continue
        for name in re.findall(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(', body):
            target = functions.get(name, '')
            if (not target or name == parent or name in terminal or name in selectors
                    or re.search(r'crawl|extract|decode|unpack|probe|validat', name, re.I)):
                continue
            # Require a selector directly called by the observed dispatcher.
            # Names support compact helpers; markup supports opaque names.
            if (re.search(r'player|server|episode', name, re.I)
                    or re.search(r'<(?:iframe|option|select)\b|data-(?:player|server)', target, re.I)):
                selectors.append(name)
    selectors.sort(key=lambda name: bool(re.search(r'episode', name, re.I)))
    if not selectors:
        return {}
    return {'reason': 'short_terminal_media_source', 'selector_functions': selectors[:3],
            'terminal_functions': terminal[:2], 'fixtures': fixtures[:4]}


def non_improving_functions(source, live):
    """Rotate edit locality after a proved, rejected experiment with no gain.

    This is temporary prompt selection, not a permanent function blacklist.
    The current call graph remains available to select neighboring helpers.
    """
    feedback = verification_feedback(live.get('previous_verification'))
    if not feedback.get('executionObserved') or not feedback.get('materializedMutationObserved'):
        return []
    if feedback.get('reason') not in {'insufficient_playable_stream_proof', 'no_strict_runtime_improvement',
                                     'variant_coverage_no_verified_dimension_gain',
                                     'decoded_repair_no_new_fixture_control'}:
        return []
    if feedback.get('baseline') != feedback.get('candidate'):
        return []

    def normalize(text):
        return re.sub(r'\bconsole\s*\.\s*(?:error|log|warn|info|debug|trace|dir)\b',
                      '__nuvioProviderSilentLog', text)

    finds = [normalize(str(row.get('find') or '')) for row in rows(live.get('previous_executed_edits'), 2)
             if isinstance(row, dict) and len(str(row.get('find') or '')) >= 8]
    names = []
    source = str(source or '')
    for match in re.finditer(r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', source):
        end = javascript_function_end(source, match.start())
        if end is None or end < 0:
            continue
        body = normalize(source[match.start():end])
        if any(find in body for find in finds) and match.group(1) not in names:
            names.append(match.group(1))
    return names[:4]


def observed_failure_class(current, live):
    """Refine broad census labels using the source-validated current preflight."""
    if current not in {'variant_coverage_gap', 'candidate_replay_gap'}:
        return current
    failed = {row['fixture'] for row in fixture_evidence(live.get('fixture_evidence'))
              if row['streamsReturned'] == 0}
    if not failed:
        return current
    observations = [row for row in network_evidence(live.get('network_evidence'))
                    if row['fixture'] in failed]
    if not observations:
        return current
    # A plain replay request remains non-mutating. Only the measured rejection
    # of a short terminal source can establish a different current failure.
    if current == 'candidate_replay_gap' and not _short_media_fixtures(live, observations):
        return current
    return 'chain_terminal_gap' if any(row['stage'] in {'player', 'source', 'media'}
                                      for row in observations) else 'route_proven_gap'


def executed_runtime_source(context, live):
    preferred = str(context.get('preferredRuntimeMutationSource') or '')
    source = str(context.get('runtimeMutationSource') or '')
    # Runtime source is the published provider-owned prefix. Keep the boundary
    # explicit even for callers supplying their own RepairRequest context.
    for marker in ('/* STARTFIX:CORE.', '/* NUVIO_GLOBAL_CORE_START_BOUNDARY_V1 */'):
        source = source.split(marker, 1)[0]
    for name in identifiers(live.get('active_functions'), 6):
        pattern = r'\b(?:async\s+)?function\s+' + re.escape(name) + r'\s*\('
        if re.search(pattern, source) and not re.search(pattern, preferred):
            return source
    return preferred


def executed_helper_context(source, live):
    for name in identifiers(live.get('active_functions'), 6):
        for match in re.finditer(r'\b(?:async\s+)?function\s+' + re.escape(name) + r'\s*\(', source):
            end = javascript_function_end(source, match.start())
            if end is not None and 1800 < end - match.start() <= 8000:
                return [{'name': name, 'source': source[match.start():end], 'read_only': True}]
    return []
