"""Regression: a syntactically valid guard-only edit must not erase media traversal.

The real source-pinned Sekai private FORCE run produced a provider Bloc edit
that removed every runtime/source append and added only an episode guard. The
generative compiler must reject this class of edit before canonical apply.
"""
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import (
    _compact_edit_to_mutation, _reject_causally_empty_deletion,
)
from niakvio_brain_llm.prompting import build_force_prompt_payload


class TerminalProducerPreservationTests(unittest.TestCase):
    def setUp(self):
        self.branch = (
            'if (hasPlayers(meta)) { '
            'const candidates = getPlayerUrls(meta); '
            'const runtime = await resolveRuntimeApi(candidates); '
            'if (runtime.length) streams.push(...runtime); '
            'else { const crawled = await crawlDirectMedia(candidates); '
            'if (crawled.length) streams.push(...crawled); } '
            'if (cached.length) streams.push(...cached); '
            '}'
        )
        self.guard_only = (
            'if (hasPlayers(meta)) { '
            'const episodeMarker = checkEpisode(detailUrl, season, episode); '
            'if (episodeMarker.marked && !episodeMarker.matches) continue; '
            '}'
        )

    def test_reject_guard_only_erasure_of_all_terminal_stream_paths(self):
        with self.assertRaisesRegex(ValueError, 'all terminal stream producers erased'):
            _reject_causally_empty_deletion('route_proven_gap', self.branch, self.guard_only)
        for failure_class in ('chain_terminal_gap', 'media_extraction_gap', 'content_identity_gap'):
            with self.subTest(failure_class=failure_class):
                with self.assertRaisesRegex(ValueError, 'all terminal stream producers erased'):
                    _reject_causally_empty_deletion(failure_class, self.branch, self.guard_only)

    def test_guard_can_be_added_without_deleting_terminal_producers(self):
        guard_plus_original = self.branch.replace(
            'const candidates =',
            'const marker = checkEpisode(detailUrl, season, episode); '
            'if (marker.marked && !marker.matches) continue; const candidates =',
        )
        _reject_causally_empty_deletion('route_proven_gap', self.branch, guard_plus_original)
        # A bounded legitimate rewrite may change push into assignment/return.
        assignment = 'if (hasPlayers(meta)) { streams = streams.concat(await resolveRuntimeApi(getPlayerUrls(meta))); }'
        _reject_causally_empty_deletion('route_proven_gap', self.branch, assignment)
        returned = 'if (hasPlayers(meta)) { return await resolveRuntimeApi(getPlayerUrls(meta)); }'
        _reject_causally_empty_deletion('route_proven_gap', self.branch, returned)

    def test_unrelated_nonterminal_refactor_is_not_rejected(self):
        _reject_causally_empty_deletion(
            'route_proven_gap',
            'function aliases(q){ labels.push(q); labels.push(q.toUpperCase()); return labels; }',
            'function aliases(q){ return uniqueLabels(q); }',
        )

    def test_exact_unit_compiler_rejects_destructive_generated_bloc(self):
        source = (
            'async function discover(meta, season, episode) {\n'
            'const streams = []; const cached = [];\n'
            + self.branch + '\nreturn streams;\n}\n'
        )
        request = RepairRequest(
            provider_id='synthetic',
            status='REGRESSION PROVIDER',
            failure_class='route_proven_gap',
            allowed_mutations=['provider_bloc'],
            provider_context={
                'runtimeMutationSource': source,
                'runtimeMutationFilename': 'providers/synthetic.js',
            },
        )
        policy = {'allow_mutations': True, 'allowed_scopes': ['provider_bloc']}
        payload = build_force_prompt_payload(request, {}, policy)
        units = payload['new_bloc_target']['editable_units']
        target = next((x for x in units if 'streams.push(' in x.get('source', '')
                       and x.get('kind') == 'function_unit'), None)
        self.assertIsNotNone(target)
        edit = {
            'scope': 'provider_bloc', 'family': 'terminal_traversal',
            'unit_id': target['id'],
            'replace': self.guard_only,
        }
        with self.assertRaisesRegex(ValueError, 'all terminal stream producers erased'):
            _compact_edit_to_mutation(
                request, edit, focus_keywords=tuple(payload['structural_focus']),
            )


if __name__ == '__main__':
    unittest.main()
