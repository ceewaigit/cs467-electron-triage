#!/usr/bin/env python3
"""Independent offline evidence audit; never mutates original evidence or runner inputs.

Runs the unchanged frozen score_run against freshly reconstructed proposal exports.
Replays every recorded helper invocation, including rejected calls. The optional
--compare-saved switch reads score.json only after the independent results exist
in memory. Output is the one audit JSON file, and reconstructed inputs live in a
new temporary directory. No provider, network or GitHub call is made.
"""
import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
BASELINE = '962fac774c7845bca0da2d310ca1bdcca09c50ea'
FROZEN_COMMIT = '4baa2cb'
SKILL = '.claude/skills/issue-triage/SKILL.md'
SCRIPT = '.claude/skills/issue-triage/scripts/'
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'evals/conservative-linking'
EVIDENCE = EXP / 'evidence'
FROZEN = EVIDENCE / 'frozen'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def timestamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def load_scorer():
    spec = importlib.util.spec_from_file_location('audit_frozen_scorer', FROZEN / 'score.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    return scorer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare-saved', action='store_true')
    args = parser.parse_args()
    checks = collections.Counter()
    issues = []

    def check(condition, name, detail=None):
        checks[name] += 1
        if not condition:
            issues.append({'check': name, 'detail': detail})

    manifest = read(EVIDENCE / 'manifest.json')
    dataset = read(FROZEN / 'dataset.json')
    metadata = {case['id']: case for case in dataset['cases']}
    protocol = read(FROZEN / 'protocol.json')
    seal = read(EVIDENCE / 'sealed-proposals.json')
    collection = read(EVIDENCE / 'collection.json')
    scorer = load_scorer()
    check(git('rev-parse', 'HEAD').decode().strip() == BASELINE, 'baseline_HEAD')
    check(manifest['source_commit'] == protocol['baseline_commit'] == BASELINE, 'baseline_declared')
    check(digest(EVIDENCE / 'manifest.json') == (EVIDENCE / 'manifest.sha256').read_text().strip() == seal['manifest_sha256'], 'manifest_hash')
    check(digest(EVIDENCE / 'sealed-proposals.json') == collection['sealed_proposals_sha256'], 'seal_hash')
    for name, expected in manifest['freeze_sha256'].items():
        check(digest(FROZEN / name) == expected, 'frozen_file_hash', name)
        # The working wrapper may receive a documented post-execution reporting
        # correction; reconstruction uses the frozen wrapper and both digests
        # are recorded separately below. All frozen bytes remain mandatory.
        if name != 'experiment.py' and not name.startswith('runtime/') and (EXP / name).is_file():
            check((FROZEN / name).read_bytes() == (EXP / name).read_bytes(), 'current_matches_frozen', name)
    for name, expected in manifest['runtime_sha256'].items():
        baseline = git('show', f'{BASELINE}:{name}')
        check(hashlib.sha256(baseline).hexdigest() == expected, 'runtime_matches_baseline', name)
        check((FROZEN / 'runtime' / name).read_bytes() == baseline, 'frozen_runtime_bytes', name)
    for local, source in [('recorder.py', 'evals/tools/offline_dry_run.py'), ('score.py', 'evals/tools/score.py'), ('replay.py', 'evals/tools/replay.py')]:
        check((FROZEN / local).read_bytes() == git('show', f'{BASELINE}:{source}'), 'frozen_tool_matches_baseline', source)
    check((FROZEN / 'score.py').read_bytes() == git('show', f'{FROZEN_COMMIT}:evals/tools/score.py'), 'scorer_matches_4baa2cb')
    old_checkout_newline_differences = []
    old_paths = git('ls-tree', '-r', '--name-only', BASELINE, 'evals/golden', 'evals/tools').decode().splitlines()
    for name in old_paths:
        baseline_raw = git('show', f'{BASELINE}:{name}')
        working_raw = (ROOT / name).read_bytes() if (ROOT / name).is_file() else b''
        if working_raw != baseline_raw and working_raw.replace(b'\r\n', b'\n') == baseline_raw:
            old_checkout_newline_differences.append(name)
        working_blob = git('hash-object', '--path', name, name).strip() if (ROOT / name).is_file() else b''
        check(working_blob == git('rev-parse', f'{BASELINE}:{name}').strip(), 'old_evaluation_git_content_unchanged', name)
    check(not git('status', '--porcelain', '--', 'evals/golden', 'evals/tools').strip(), 'old_evaluation_git_status_clean')
    frozen_paths = [n for n in old_paths if n == 'evals/golden/RUBRIC.md' or n == 'evals/tools/score.py' or re.fullmatch(r'evals/golden/cases/[^/]+/(input|expected)\.json', n)]
    for name in frozen_paths:
        check((ROOT / name).read_bytes() == git('show', f'{FROZEN_COMMIT}:{name}'), 'golden_matches_4baa2cb', name)
    old_policy = (FROZEN / 'policies/original-SKILL.md').read_text()
    new_policy = (FROZEN / 'policies/candidate-SKILL.md').read_text()
    def sections(text):
        parts = re.split(r'(?m)^(### .+)\n', text)
        return {'preamble': parts[0], **{parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}}
    a, b = sections(old_policy), sections(new_policy)
    changed_sections = [key for key in set(a) | set(b) if a.get(key) != b.get(key)]
    check(set(changed_sections) == {'### 2. Component label (0–2)', '### 4. Similar earlier issues'}, 'only_two_skill_sections_differ', changed_sections)
    check(old_policy.encode() == git('show', f'{BASELINE}:{SKILL}'), 'original_policy_baseline')
    working_policy = (ROOT / SKILL).read_bytes()
    check(working_policy in (old_policy.encode(), new_policy.encode()), 'working_policy_matches_frozen_arm')
    working_policy_arm = 'original' if working_policy == old_policy.encode() else 'candidate'

    # Independently reproduce selection without executing the selection author code.
    selection = read(FROZEN / 'selection.json')
    source_path = ROOT / selection['source']
    check(digest(source_path) == selection['source_sha256'], 'selection_source_hash')
    source_rows = [json.loads(line) for line in source_path.read_text().splitlines()]
    by_number = {row['number']: row for row in source_rows}
    previous_numbers, previous_files = set(), []
    for path in sorted((ROOT / 'evals').rglob('input.json')):
        if EXP in path.parents or {'actual', 'results', 'logs'} & set(path.parts):
            continue
        data = read(path)
        match = re.search(r'electron/electron/issues/(\d+)', data.get('source', ''))
        if match:
            previous_numbers.add(int(match[1]))
        elif re.fullmatch(r'e\d+', data.get('id', '')):
            previous_numbers.add(int(data['id'][1:]))
        previous_files.append(str(path.relative_to(ROOT)))
    check(previous_files == selection['previous_case_inputs_inspected'], 'prior_inputs_inventory')
    check(sorted(previous_numbers) == selection['previous_real_numbers_excluded'], 'prior_numbers_excluded')
    rng, selected, eligible_counts = random.Random(4672026), [], {}
    for month in ('2026-04', '2026-05', '2026-06'):
        eligible = sorted(row['number'] for row in source_rows if row['created_at'].startswith(month)
                          and row.get('author_type') != 'Bot' and not (row.get('author') or '').lower().endswith('[bot]')
                          and row['author_association'].upper() not in {'MEMBER', 'OWNER', 'COLLABORATOR'}
                          and row['number'] not in previous_numbers)
        chosen = rng.sample(eligible, 8)
        check(eligible == selection['months'][month]['eligible_sorted'], 'selection_eligible_set', month)
        check(chosen == selection['months'][month]['selected_in_draw_order'], 'selection_random_draw', month)
        selected.extend(f'e{n}' for n in chosen)
        eligible_counts[month] = len(eligible)
    check(selected == selection['case_order'], 'selection_order')
    for case_id in selected:
        opening = read(FROZEN / 'cases' / case_id / 'input.json')
        source = by_number[int(case_id[1:])]
        for key, source_key in [('title', 'title'), ('body', 'body'), ('author_association', 'author_association'), ('labels_at_open', 'labels_at_open'), ('as_of', 'created_at'), ('body_source', 'body_source')]:
            check(opening[key] == source[source_key], 'opening_source_field', f'{case_id}/{key}')
        check(opening['source'] == f'https://github.com/electron/electron/issues/{case_id[1:]}', 'opening_source_URL', case_id)
    check(collections.Counter(c['group'] for c in metadata.values()) == {'historical': 24, 'constructed': 6}, 'case_counts')

    # Verify annotation runtime provenance and pre-execution review hash anchors.
    provenance = read(FROZEN / 'annotation-provenance.json')
    for name, expected in provenance['source_hashes'].items():
        check(hashlib.sha256(git('show', f'{BASELINE}:{name}')).hexdigest() == expected, 'annotation_source_baseline', name)
    review = (FROZEN / 'pre-execution-review.md').read_text()
    review_time = timestamp(re.search(r'Final sign-off UTC: ([^\s]+)', review)[1].rstrip('.'))
    for name in ['dataset.json', 'selection.json', 'annotation-provenance.json']:
        check(digest(FROZEN / name) in review, 'review_hash_anchor', name)
    check(digest(EXP / 'ANNOTATION_NOTES.md') in review, 'review_annotation_notes_hash')
    for case_id, case_metadata in metadata.items():
        for name, identity in case_metadata['files'].items():
            check(digest(FROZEN / identity['path']) == identity['sha256'], 'dataset_case_hash', identity['path'])
        for name in ('input.json', 'expected.json'):
            check(digest(FROZEN / 'cases' / case_id / name) in review, 'review_case_hash_anchor', f'{case_id}/{name}')
    prepared_time, sealed_time = timestamp(manifest['prepared_at_utc']), timestamp(seal['sealed_at_utc'])
    check(timestamp(protocol['created_at_utc']) < timestamp(dataset['annotated_at_utc']) < review_time < prepared_time < sealed_time, 'protocol_annotation_review_prepare_seal_order')

    # Rebuild exact input-only snapshots in an unused temporary location.
    temporary = Path(tempfile.mkdtemp(prefix='conservative-independent-', dir='/private/tmp'))
    reconstructed = temporary / 'workspaces'
    reproduced = subprocess.run([sys.executable, str(FROZEN / 'experiment.py'), '--experiment', str(EXP), '--repo', str(ROOT), 'reproduce', '--destination', str(reconstructed)], cwd=ROOT, capture_output=True, text=True)
    check(reproduced.returncode == 0, 'reproduce_success', reproduced.stderr)
    original_root = Path('/tmp/cs467-conservative-workspace.txt').read_text().strip()
    original_root = Path(original_root)

    planned_batches = []
    arm_order = ['original', 'candidate']
    random.Random(4672026).shuffle(arm_order)
    for repetition in (1, 2):
        ordered = sorted(metadata)
        random.Random(4672026 + repetition).shuffle(ordered)
        for arm_index, arm in enumerate(arm_order, 1):
            for offset in range(0, 30, 10):
                planned_batches.append({'id': f's{len(planned_batches)+1:03}', 'arm': arm, 'opaque_arm': f'v{arm_index:02}', 'repetition': repetition, 'seed': 4672026 + repetition,
                                       'cases': [(case_id, f'd{i+1:03}') for i, case_id in enumerate(ordered[offset:offset+10], offset)]})
    for planned, recorded in zip(planned_batches, manifest['batches']):
        check(all(planned[k] == recorded[k] for k in ('id', 'arm', 'opaque_arm', 'repetition', 'seed')) and planned['cases'] == [(c['case_id'], c['token']) for c in recorded['cases']], 'batch_mapping_and_seed', recorded['id'])

    events_min, events_max, rejections = [], [], []
    rows, all_session_keys, pairing = [], set(), collections.defaultdict(list)
    helper_counts = collections.Counter()
    for batch in manifest['batches']:
        batch_root = reconstructed / batch['id']
        prompt = batch_root / 'INSTRUCTIONS.md'
        check(digest(prompt) == batch['instructions_sha256'] == digest(EVIDENCE / 'batch-prompts' / f"{batch['id']}.md"), 'batch_prompt_hash', batch['id'])
        check(prompt.read_bytes() == (original_root / batch['id'] / 'INSTRUCTIONS.md').read_bytes(), 'original_batch_prompt', batch['id'])
        prompt_text = prompt.read_text()
        check(all(text in prompt_text for text in ['Start fresh without parent chat history', 'Handle only these ten cases', 'other batches, the parent repository, evaluator files, expected outcomes', 'first final decision', 'Never edit']), 'batch_blinding_instructions', batch['id'])
        check((EVIDENCE / 'dispatch-prompts' / f"{batch['id']}.txt").exists() and (EVIDENCE / 'batch-completions' / f"{batch['id']}.txt").exists(), 'batch_dispatch_completion_present', batch['id'])
        check(len(batch['cases']) == 10, 'batch_size', batch['id'])
        previous_end = None
        for case in batch['cases']:
            case_id, token = case['case_id'], case['token']
            key = f"{batch['id']}/{token}"
            check(key not in all_session_keys, 'unique_session', key)
            all_session_keys.add(key)
            directory = batch_root / 'cases' / token
            checkout = directory / 'checkout'
            original_directory = original_root / batch['id'] / 'cases' / token
            actual_directory = EXP / 'cases' / case_id / 'actual' / batch['arm']
            logs = actual_directory / 'logs' / f"run-{batch['repetition']}"
            actual = read(actual_directory / f"run-{batch['repetition']}.json")
            proposal = read(logs / 'proposal.json')
            events = [json.loads(line) for line in (logs / 'transcript.jsonl').read_text().splitlines()]
            context = read(directory / 'context.json')
            check(digest(directory / 'context.json') == case['context_sha256'] == digest(logs / 'context.json'), 'context_hash', key)
            check((directory / 'context.json').read_bytes() == (original_directory / 'context.json').read_bytes(), 'original_context_identical', key)
            expected_files = set(context['file_sha256'])
            reconstructed_files = {str(p.relative_to(checkout)) for p in checkout.rglob('*') if p.is_file()}
            original_files = {str(p.relative_to(original_directory / 'checkout')) for p in (original_directory / 'checkout').rglob('*') if p.is_file()}
            check(reconstructed_files == expected_files, 'input_only_exact_inventory', key)
            check(original_files == expected_files, 'original_input_only_exact_inventory', {'session': key, 'extra': sorted(original_files - expected_files)})
            check(not any(re.search(r'(^|/)(evals|expected\.json|annotation\.json|score\.json|dataset\.json)(/|$)', p) for p in expected_files), 'no_gold_paths', key)
            for name, expected in context['file_sha256'].items():
                check(digest(checkout / name) == expected == digest(original_directory / 'checkout' / name), 'snapshot_file_hash', f'{key}/{name}')
            check(digest(checkout / '.triage/issue.json') == case['normalized_input_sha256'] == digest(logs / 'issue.json'), 'normalized_input_hash', key)
            opening = read(FROZEN / 'cases' / case_id / 'input.json')
            corpus_lines = (checkout / 'data/issue-corpus.jsonl').read_bytes().splitlines()
            source_corpus = (FROZEN / 'runtime/data/issue-corpus.jsonl').read_bytes() if metadata[case_id]['group'] == 'historical' else (FROZEN / 'cases' / case_id / 'corpus.jsonl').read_bytes()
            expected_corpus = b''.join(line + b'\n' for line in source_corpus.splitlines() if json.loads(line)['created_at'] < opening['as_of'])
            check((checkout / 'data/issue-corpus.jsonl').read_bytes() == expected_corpus, 'strict_earlier_corpus_bytes', key)
            check(len(corpus_lines) == context['earlier_corpus_rows'] == metadata[case_id]['corpus_rows'], 'corpus_row_count', key)
            pairing[(case_id, batch['repetition'])].append({name: value for name, value in context['file_sha256'].items() if name != SKILL})
            check(digest(logs / 'proposal.json') == seal['sessions'][key]['proposal_sha256'] == actual['proposal_sha256'], 'first_proposal_seal', key)
            check(digest(logs / 'transcript.jsonl') == seal['sessions'][key]['transcript_sha256'], 'transcript_seal', key)
            for name in ('proposal.json', 'transcript.jsonl'):
                check((logs / name).read_bytes() == (original_directory / name).read_bytes(), 'original_evidence_identical', f'{key}/{name}')
            for name, expected in collection['exports'][key]['file_sha256'].items():
                check(digest(EXP / name) == expected, 'export_collection_hash', name)
            check(events[0]['event'] == 'context' and events[-1]['event'] == 'assistant_decision' and sum(e['event'] == 'assistant_decision' for e in events) == 1 and events[-1]['content'] == proposal, 'one_first_decision_at_end', key)
            times = [timestamp(e['time_utc']) for e in events]
            check(times == sorted(times) and prepared_time < times[0] < times[-1] < sealed_time, 'event_chronology', key)
            if previous_end is not None:
                check(previous_end < times[0], 'batch_case_execution_order', key)
            previous_end = times[-1]
            events_min.append(times[0]); events_max.append(times[-1])
            context_names = ['AGENTS.md', 'CLAUDE.md', '.github/workflows/issue-triage.md', SKILL, '.triage/issue.json']
            displayed = '\n\n'.join(f'--- {name} ---\n{(checkout / name).read_text()}' for name in context_names)
            check(all(e['content'] == displayed for e in events if e['event'] == 'context'), 'recorded_context_exact', key)
            markdown = '# Recorded coding-assistant session\n\nProposed actions only; no external writes.\n'
            for i, event in enumerate(events, 1):
                markdown += f"\n## {i}. {event['event']} — {event.get('time_utc', 'timestamp unavailable')}\n\n"
                markdown += event['content'] + '\n' if event['event'] == 'context' else '````json\n' + json.dumps(event, indent=2, ensure_ascii=False) + '\n````\n'
            check((logs / 'transcript.md').read_text() == markdown, 'markdown_jsonl_equivalence', key)
            validations = read(logs / 'export-validation.json')
            script_events = [e for e in events if e['event'] == 'script']
            for kind, calls in [('recorded', script_events), ('export', validations)]:
                for index, event in enumerate(calls):
                    command = event['command']
                    check(command[0] == 'python3' and command[1] in [SCRIPT + n + '.py' for n in ('triage_checks', 'check_labels', 'render_comment')], 'allowlisted_helper_command', {'session': key, 'command': command})
                    result = subprocess.run([sys.executable, *command[1:]], cwd=checkout, capture_output=True, text=True, env={'PATH': os.defpath, 'HOME': str(checkout)}, timeout=30)
                    matched = (result.returncode, result.stdout, result.stderr) == (event['exit_code'], event['stdout'], event['stderr'])
                    check(matched, 'helper_replay_exact', {'session': key, 'kind': kind, 'index': index, 'command': command, 'actual_exit': result.returncode})
                    helper_counts[kind] += 1
                    helper_counts[Path(command[1]).stem] += 1
                    if event['exit_code'] != 0:
                        rejections.append({'session': key, 'kind': kind, 'command': command, 'exit_code': event['exit_code'], 'stdout': event['stdout'], 'stderr': event['stderr'], 'reproduced': matched})
            labels, comment, comment_request = [], None, None
            check(proposal['writes_executed'] is False, 'proposal_no_external_writes', key)
            types = [item['type'] for item in proposal['items']]
            check(len(types) == len(set(types)) and set(types) <= {'add_labels', 'triage_comment', 'noop'} and ('noop' not in types or len(types) == 1), 'proposal_action_schema', key)
            for item in proposal['items']:
                if item['type'] == 'add_labels':
                    labels = item['labels']
                    check(any(e['exit_code'] == 0 and e['command'] == ['python3', SCRIPT + 'check_labels.py', *labels] for e in script_events), 'exact_labels_validated_before_decision', key)
                elif item['type'] == 'triage_comment':
                    comment_request = item
                    command = ['python3', SCRIPT + 'render_comment.py', '--kinds', item['kinds'], '--refs', item['refs']]
                    rendered = subprocess.run([sys.executable, *command[1:]], cwd=checkout, capture_output=True, text=True, env={'PATH': os.defpath, 'HOME': str(checkout)}, timeout=30)
                    check(rendered.returncode == 0, 'independent_final_render_valid', key)
                    if rendered.returncode == 0:
                        comment = rendered.stdout.split('-----BEGIN COMMENT-----\n', 1)[1].split('\n-----END COMMENT-----', 1)[0]
                    def same_render_arguments(recorded):
                        if recorded[:2] != command[:2]:
                            return False
                        options = dict(zip(recorded[2::2], recorded[3::2]))
                        return options.get('--kinds') == item['kinds'] and options.get('--refs', '') == item['refs']
                    check(any(e['exit_code'] == 0 and same_render_arguments(e['command']) and e['stdout'] == rendered.stdout for e in script_events), 'exact_comment_validated_before_decision', key)
            check(any(e['exit_code'] == 0 and e['command'][1] == SCRIPT + 'triage_checks.py' for e in script_events), 'triage_checks_before_decision', key)
            check(labels == actual['labels_added'] and comment == actual['comment'] and comment_request == actual['comment_request'] and actual['other_writes'] == [] and actual['scored'] and not actual['invalid_final_proposal'], 'export_faithful_to_first_proposal', key)
            check(len(labels) <= 3 and sum(l.startswith('component/') for l in labels) <= 2, 'label_count_bounds', key)
            kinds, refs = scorer.parse_comment(comment)
            check_report = json.loads(next(e['stdout'].split('\n', 1)[1] for e in script_events if e['exit_code'] == 0 and e['command'][1] == SCRIPT + 'triage_checks.py'))
            check(not (refs & set(check_report['issues_linked_by_reporter'])), 'no_reporter_link_repeated', key)
            requested_refs = re.findall(r'\d{4,6}', comment_request['refs']) if comment_request else []
            check(len(requested_refs) <= 3 and set(map(int, requested_refs)) == refs, 'all_requested_refs_preserved_and_bounded', key)
            check(check_report['skip'] is None or (not labels and not comment), 'skip_enforced', key)
            check('security' not in kinds or (kinds == {'security'} and 'blocked/need-repro' not in labels), 'security_exclusivity_and_no_repro_label', key)
            result = scorer.score_run(read(FROZEN / 'cases' / case_id / 'expected.json'), {'labels_added': labels, 'comment': comment, 'other_writes': []})
            expected = read(FROZEN / 'cases' / case_id / 'expected.json')
            allowed_components = {l for l in expected['labels']['required'] + expected['labels']['acceptable'] + [l for group in expected['labels']['one_of'] for l in group] if l.startswith('component/')}
            positive = {control: ('similar' in kinds and bool(refs & set(metadata[case_id]['coverage_supported_refs']))) if control == 'link' else bool(set(labels) & allowed_components) for control in metadata[case_id]['positive_controls']}
            supported = set(metadata[case_id]['coverage_supported_refs']) | set(metadata[case_id].get('acceptable_optional_refs', []))
            unsupported = sorted(refs - supported)
            required_labels = set(expected['labels']['required']) | {l for group in expected['labels']['one_of'] for l in group}
            rows.append({'case_id': case_id, 'arm': batch['arm'], 'repetition': batch['repetition'], 'group': metadata[case_id]['group'], **result,
                         'scored': True, 'missed_required_actions': sum(f.startswith('missing') for f in result['fails']), 'labels': sorted(labels), 'comment_kinds': sorted(kinds), 'refs': sorted(refs),
                         'unsupported_refs': unsupported, 'strict_coverage_only_unsupported_refs': sorted(refs - set(metadata[case_id]['coverage_supported_refs'])),
                         'positive_controls': metadata[case_id]['positive_controls'], 'positive_control_coverage': positive,
                         'discretionary_labels': sorted(set(labels) - required_labels), 'discretionary_links': sorted(refs) if 'similar' not in expected['comment']['required_kinds'] else []})
    check(len(rows) == len(all_session_keys) == 120 and all_session_keys == set(seal['sessions']) == set(collection['exports']), 'complete_120_sessions')
    for pair, contexts in pairing.items():
        check(len(contexts) == 2 and contexts[0] == contexts[1], 'paired_inputs_identical_except_policy', str(pair))
    check(len(pairing) == 60, 'sixty_pairs')

    def summary(group, arm, repetition):
        chosen = [r for r in rows if (group == 'all' or r['group'] == group) and r['arm'] == arm and (repetition == 'pooled' or r['repetition'] == repetition)]
        return {'planned': len(chosen), 'valid': len(chosen), 'full_case_passes': sum(r['pass'] for r in chosen), 'weighted_error_cost_total': sum(r['cost'] for r in chosen),
                'mean_weighted_error_cost': sum(r['cost'] for r in chosen) / len(chosen), 'missed_required_actions': sum(r['missed_required_actions'] for r in chosen),
                'safety_failures': sum(r['safety'] for r in chosen), 'invalid_final_proposals': 0, 'unsupported_references': sum(len(r['unsupported_refs']) for r in chosen),
                'discretionary_labels': sum(len(r['discretionary_labels']) for r in chosen), 'discretionary_links': sum(len(r['discretionary_links']) for r in chosen)}
    summaries = {group: {arm: {str(rep): summary(group, arm, rep) for rep in (1, 2, 'pooled')} for arm in ('original', 'candidate')} for group in ('historical', 'constructed', 'all')}
    gates = {'complete_valid_coverage': len(rows) == 120, 'no_candidate_safety_or_invalid_final_proposal': all(not r['safety'] for r in rows if r['arm'] == 'candidate')}
    for rep in (1, 2):
        original, candidate = (summaries['historical'][arm][str(rep)] for arm in ('original', 'candidate'))
        gates[f'run_{rep}_historical_cost_strictly_lower'] = candidate['mean_weighted_error_cost'] < original['mean_weighted_error_cost']
        gates[f'run_{rep}_historical_passes_not_lower'] = candidate['full_case_passes'] >= original['full_case_passes']
        gates[f'run_{rep}_historical_omissions_not_higher'] = candidate['missed_required_actions'] <= original['missed_required_actions']
        gates[f'run_{rep}_constructed_passes_not_lower'] = summaries['constructed']['candidate'][str(rep)]['full_case_passes'] >= summaries['constructed']['original'][str(rep)]['full_case_passes']
        positives = [r for r in rows if r['arm'] == 'candidate' and r['group'] == 'constructed' and r['repetition'] == rep and r['positive_controls']]
        gates[f'run_{rep}_all_positive_controls_pass'] = bool(positives) and all(r['pass'] and all(r['positive_control_coverage'].values()) for r in positives)
        gates[f'run_{rep}_unsupported_references_not_higher'] = summaries['all']['candidate'][str(rep)]['unsupported_references'] <= summaries['all']['original'][str(rep)]['unsupported_references']
    coverage = {}
    for group in ('historical', 'constructed'):
        coverage[group] = {}
        for arm in ('original', 'candidate'):
            coverage[group][arm] = {}
            for rep in (1, 2):
                selected_rows = [r for r in rows if r['group'] == group and r['arm'] == arm and r['repetition'] == rep]
                coverage[group][arm][str(rep)] = {control: {'covered': sum(r['positive_control_coverage'].get(control, False) for r in selected_rows), 'eligible': sum(control in r['positive_controls'] for r in selected_rows)} for control in ('link', 'component')}
                coverage[group][arm][str(rep)]['supported_link_opportunities'] = {'covered': sum(bool(set(r['refs']) & set(metadata[r['case_id']]['coverage_supported_refs'])) for r in selected_rows if metadata[r['case_id']]['coverage_supported_refs']), 'eligible': sum(bool(metadata[r['case_id']]['coverage_supported_refs']) for r in selected_rows)}
    changes = []
    for rep in (1, 2):
        for case_id in sorted(metadata):
            pair = {r['arm']: r for r in rows if r['case_id'] == case_id and r['repetition'] == rep}
            difference = {field: {arm: pair[arm][field] for arm in ('original', 'candidate')} for field in ('labels', 'comment_kinds', 'refs') if pair['original'][field] != pair['candidate'][field]}
            if difference:
                changes.append({'case_id': case_id, 'group': metadata[case_id]['group'], 'repetition': rep, 'changed_actions': difference, **{arm + '_score': {k: pair[arm][k] for k in ('pass', 'cost', 'fails')} for arm in ('original', 'candidate')}})
    result = {'initial_review_calculated_scores_before_saved_score_or_README_results': True, 'audit_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'baseline_commit': BASELINE, 'scorer_sha256': digest(FROZEN / 'score.py'), 'manifest_sha256': digest(EVIDENCE / 'manifest.json'), 'collection_sha256': digest(EVIDENCE / 'collection.json'),
              'independently_reconstructed_summary': summaries, 'primary_decision': {'gates': gates, 'accepted': all(gates.values())}, 'positive_coverage': coverage,
              'changed_actions': changes, 'case_runs': rows, 'missed_required_actions': [r for r in rows if r['missed_required_actions']], 'verification_counts': dict(checks), 'verification_failures': issues,
              'helper_calls_reexecuted': dict(helper_counts), 'preserved_rejected_calls': rejections, 'eligibility_counts': eligible_counts,
              'chronology': {'review_accepted': review_time.isoformat(), 'manifest_prepared': prepared_time.isoformat(), 'first_event': min(events_min).isoformat(), 'last_decision': max(events_max).isoformat(), 'all_proposals_sealed': sealed_time.isoformat()},
              'reconstructed_workspace': str(reconstructed), 'changed_policy_sections': sorted(changed_sections), 'working_policy_arm_at_audit': working_policy_arm, 'working_experiment_sha256_at_audit': digest(EXP / 'experiment.py'), 'frozen_experiment_sha256': digest(FROZEN / 'experiment.py'), 'old_checkout_CRLF_differences_with_unchanged_git_content': old_checkout_newline_differences,
              'limitations': ['Local recorder and timestamps are self-reported evidence, not signed provider transcripts or proof of filesystem isolation.', 'Dispatch instructions request fresh no-parent-history contexts; the preserved files cannot independently prove model context isolation or absence of unrecorded tool use.', 'Exact backend model identifier and metered usage are unavailable.', 'Annotation and review were AI-assisted, with disclosed limited prior aggregate-result exposure; expectations remain frozen.', 'Constructed controls are a separate diagnostic cohort; two repetitions on the same sampled cases do not establish statistical significance or general superiority.']}
    # Persist calculations BEFORE opening the author\'s score report.
    output = EVIDENCE / 'independent-check-results.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    if args.compare_saved:
        saved = read(EVIDENCE / 'score.json')
        differences = []
        for key, own in [('summary', summaries), ('changed_actions', changes)]:
            if saved[key] != own:
                differences.append(key)
        if saved['primary_decision']['gates'] != gates or saved['primary_decision']['accepted'] != all(gates.values()):
            differences.append('primary_decision')
        own_rows = {(r['case_id'], r['arm'], r['repetition']): r for r in rows}
        for saved_row in saved['case_runs']:
            own = own_rows[(saved_row['case_id'], saved_row['arm'], saved_row['repetition'])]
            for key in own:
                if key != 'strict_coverage_only_unsupported_refs' and saved_row[key] != own[key]:
                    differences.append(f"case_runs/{own['case_id']}/{own['arm']}/{own['repetition']}/{key}")
        result['comparison_after_independent_calculation'] = {'differences': differences, 'saved_score_sha256': digest(EVIDENCE / 'score.json')}
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'summary': summaries, 'primary_decision': result['primary_decision'], 'coverage': coverage, 'verification_failures': issues, 'helper_calls': dict(helper_counts), 'rejections': rejections, 'saved_comparison': result.get('comparison_after_independent_calculation'), 'output': str(output)}, indent=2))
    return 1 if issues or result.get('comparison_after_independent_calculation', {}).get('differences') else 0


if __name__ == '__main__':
    sys.exit(main())
