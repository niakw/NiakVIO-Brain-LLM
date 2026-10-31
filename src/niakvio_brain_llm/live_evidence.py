"""Bound live diagnostics to structural facts, never response scalar values."""
import json
import re
from .source_units import javascript_function_end

IDENTIFIER = re.compile(r"[A-Za-z_$][\w$-]{0,47}")
SENSITIVE = re.compile(r"key|token|auth|signature|secret|password|cookie|session|nonce", re.I)

def rows(value, limit):
    return value[:limit] if isinstance(value, list) else []


def count(value, maximum=100000):
    return max(0, min(maximum, value)) if type(value) is int else 0


def identifiers(values, limit=16):
    return [name for name in values if isinstance(name, str) and IDENTIFIER.fullmatch(name)
            and not SENSITIVE.search(name)][:limit] if isinstance(values, list) else []


def player_markup(value):
    if not isinstance(value, dict):
        return {}
    attributes = {'src', 'data-src', 'href', 'value', 'data-url', 'data-link', 'data-player',
                  'data-embed', 'data-video', 'data-code', 'data-iframe', 'data-source',
                  'data-player-id', 'data-index', 'data-server'}
    kinds = {'empty', 'absolute_url', 'relative_url', 'fragment', 'inline_markup',
             'escaped_markup', 'encoded_markup', 'encoded_url', 'other'}
    result = []
    for row in rows(value.get('rows'), 8):
        if not isinstance(row, dict) or row.get('tag') not in {
            'iframe', 'video', 'source', 'a', 'button', 'option', 'div', 'li', 'input'
        }:
            continue
        raw = row.get('value_kinds')
        projected = {name: kind for name, kind in raw.items()
                     if name in attributes and isinstance(kind, str) and kind in kinds} if isinstance(raw, dict) else {}
        projected = dict(list(projected.items())[:8])
        if projected:
            total = count(row.get('count'), 128)
            result.append({'tag': row['tag'], 'value_kinds': projected, 'count': total,
                           'distinct_values': min(total, count(row.get('distinct_values'), 128))})
    return {'rows': result, 'sampled_chars': count(value.get('sampled_chars'), 131072),
            'truncated': value.get('truncated') is True}


def response_structure(value):
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
        return {"kind": kind, "fields": fields}
    if kind == "html":
        result = {"kind": kind, "tags": [
            {"tag": row["tag"], "attributes": identifiers(row.get("attributes"))}
            for row in rows(value.get("tags"), 8) if isinstance(row, dict)
            and row.get("tag") in {"iframe", "script", "video", "source", "a", "button", "select", "option"}
        ], "variables": identifiers(value.get("variables"))}
        if isinstance(value.get('player_markup'), dict):
            result['player_markup'] = player_markup(value['player_markup'])
        return result
    return {"kind": kind} if kind in {"text", "binary"} else {}


def network_evidence(values):
    result = []
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
            "response_structure": response_structure(row.get("response_structure")),
            "announced_players": count(row.get("announced_players"), 256),
        }
        media = row.get('media_observation')
        if isinstance(media, dict):
            item['media_observation'] = {
                'signature': media.get('signature') if media.get('signature') in
                    {'unknown', 'mp4', 'ebml', 'mpegts', 'hls', 'html'} else 'unknown',
                'durationSeconds': count(media.get('durationSeconds'), 1209600)
                    if type(media.get('durationSeconds')) is int else None,
                'bytesSampled': count(media.get('bytesSampled'), 65536),
                'readState': media.get('readState') if media.get('readState') in
                    {'not_read', 'data', 'empty', 'complete', 'error'} else 'not_read',
                'cancelState': media.get('cancelState') if media.get('cancelState') in
                    {'not_requested', 'requested', 'complete', 'error'} else 'not_requested',
            }
        result.append(item)
    if len(result) <= 8:
        return result
    # Repeated player replies must not hide the episode/lookup context. Reserve
    # one event per fixture/stage, then retain distinct shapes before duplicates.
    primary, alternatives, duplicates = [], [], []
    phases, shapes = set(), set()
    for item in result:
        shape = dict(item)
        structure = dict(shape['response_structure'])
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
    return (primary + alternatives + duplicates)[:8]


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
    result["candidate_network"] = network_evidence(value.get("candidate_network"))
    return result


def short_media_source_focus(source, live):
    """Expose upstream selectors when a measured terminal source is too short.

    This only chooses model edit surfaces. It neither accepts a source nor
    changes media/identity validation, and requires the same failed fixture.
    """
    expected = {row['fixture']: row['expectedDurationSeconds']
                for row in fixture_evidence(live.get('fixture_evidence'))
                if row['streamsReturned'] == 0 and row.get('expectedDurationSeconds', 0) >= 600}
    observations = network_evidence(live.get('network_evidence'))
    failed = {}
    for row in observations:
        media = row.get('media_observation') or {}
        duration = media.get('durationSeconds')
        if (row['fixture'] in expected and row['status'] in {200, 206}
                and media.get('signature') == 'mp4' and type(duration) is int and 0 < duration < 60
                and media.get('bytesSampled', 0) >= 40 and media.get('readState') in {'data', 'complete'}
                and (media.get('cancelState') == 'complete' or media.get('readState') == 'complete')):
            failed[row['fixture']] = duration
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
            'terminal_functions': terminal[:2], 'fixtures': [
                {'fixture': name, 'sampledDurationSeconds': duration,
                 'expectedDurationSeconds': expected[name]} for name, duration in failed.items()
            ][:4]}


def non_improving_functions(source, live):
    """Rotate edit locality after a proved, rejected experiment with no gain.

    This is temporary prompt selection, not a permanent function blacklist.
    The current call graph remains available to select neighboring helpers.
    """
    feedback = verification_feedback(live.get('previous_verification'))
    if not feedback.get('executionObserved') or not feedback.get('materializedMutationObserved'):
        return []
    if feedback.get('reason') not in {'insufficient_playable_stream_proof', 'no_strict_runtime_improvement',
                                     'variant_coverage_no_verified_dimension_gain'}:
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
    """Current failed titles take precedence over a stale variant-risk label."""
    if current != 'variant_coverage_gap':
        return current
    failed = {row['fixture'] for row in fixture_evidence(live.get('fixture_evidence'))
              if row['streamsReturned'] == 0}
    if not failed:
        return current
    observations = [row for row in network_evidence(live.get('network_evidence'))
                    if row['fixture'] in failed]
    if not observations:
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
