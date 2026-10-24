#!/usr/bin/env python3
"""Independent local-only audit; no GitHub/provider calls; exclusive result writes.

Run from any directory. The script reads the current attempt and local Git objects.
It writes only the named new result beneath this evidence directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE.parent
ROOT = ATTEMPT.parents[1]

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_sha(commit, name):
    data = subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = HERE / args.output
    if destination.parent.resolve() != HERE.resolve():
        raise SystemExit('Output must be an immediate new file in this evidence directory.')
    if destination.exists():
        raise SystemExit('Refusing to replace a saved independent audit.')
    manifest = read(ATTEMPT / 'manifest.json')
    seal = read(ATTEMPT / 'pre-execution-seal.json')
    checks = {}
    for name, digest in seal.items():
        checks[f'sealed:{name}'] = sha(ATTEMPT / name) == digest
    for name, digest in manifest['runtime_sha256'].items():
        checks[f'working-runtime:{name}'] = sha(ROOT / name) == digest
        checks[f'source-runtime:{name}'] = git_sha(manifest['source_commit'], name) == digest
        checks[f'unchanged-runtime:{name}'] = git_sha(manifest['unchanged_runtime_from_commit'], name) == digest
    for case, names in manifest['case_sha256'].items():
        for name, digest in names.items():
            checks[f'case:{case}/{name}'] = sha(ATTEMPT / 'cases' / case / name) == digest
            checks[f'golden-copy:{case}/{name}'] = sha(ROOT / 'evals/golden/cases' / case / name) == digest
    checks['replay-hash'] = sha(ROOT / 'evals/tools/replay.py') == manifest['replay_sha256']
    checks['scorer-hash'] = sha(ROOT / 'evals/tools/score.py') == manifest['scorer_sha256']
    checks['frozen-scorer'] = git_sha('4baa2cb', 'evals/tools/score.py') == manifest['scorer_sha256']
    neutralise_namespace = {'__file__': str(ROOT / 'evals/tools/replay.py'), '__name__': 'independent_replay_audit'}
    exec(compile((ROOT / 'evals/tools/replay.py').read_text(), neutralise_namespace['__file__'], 'exec'), neutralise_namespace)
    issue_map = read(ATTEMPT / 'replay' / f"issues-{manifest['variant']}.json")
    run_map = read(ATTEMPT / 'replay' / f"runs-{manifest['variant']}.json")
    auto_controls = {}
    for case, issue in issue_map.items():
        original = read(ATTEMPT / 'cases' / case / 'input.json')
        for name in ['title', 'body']:
            checks[f'neutralisation:{case}/{name}'] = neutralise_namespace['neutralise'](original[name]) == issue[name]
        checks[f'opening-labels:{case}'] = original['labels_at_open'] == issue['labels_at_open']
        control_path = ATTEMPT / f'automatic-trigger-control-{case}.json'
        if control_path.exists():
            control = read(control_path)
            jobs = control['jobs']['jobs']
            control_checks = {
                'owner': control['issue']['author_association'] == 'OWNER',
                'one_case_issue': control['issue']['number'] in issue['issues'],
                'event': control['run']['event'] == 'issues',
                'source': control['run']['head_sha'] == manifest['source_commit'],
                'completed_skipped': control['run']['status'] == 'completed' and control['run']['conclusion'] == 'skipped',
                'all_jobs_skipped': len(jobs) > 0 and all(j['conclusion'] == 'skipped' and not j['steps'] for j in jobs),
            }
            auto_controls[case] = {'checks': control_checks, 'run_id': control['run']['id'], 'association_limit': control['association_limit']}
            checks.update({f'auto-control:{case}/{k}': v for k,v in control_checks.items()})
    for issue, row in run_map.items():
        checks[f'dispatch:{issue}/source'] = row['head_sha'] == manifest['source_commit']
        checks[f'dispatch:{issue}/ref'] = row['requested_ref'] == manifest['requested_ref']
        checks[f'dispatch:{issue}/repetition'] = row['run'] == 1
        checks[f'dispatch:{issue}/mapped'] = int(issue) in issue_map[row['case']]['issues']
    checks['dispatch-count-in-limit'] = len(run_map) <= manifest['maximum_workflow_dispatches']
    source_paths = [ATTEMPT/name for name in seal] + [ATTEMPT/'pre-execution-seal.json', ATTEMPT/'collect_artifacts.py', ROOT/'evals/tools/replay.py', ROOT/'evals/tools/score.py', ROOT/'tests/test_replay_collection.py', Path(__file__)]
    result = {
        'scope': 'Independent preparation audit before reading any coordinator score or conclusion; local reads only.',
        'source_commit': manifest['source_commit'],
        'checks': checks,
        'all_checks_passed': all(checks.values()),
        'automatic_controls': auto_controls,
        'dispatches': run_map,
        'audited_sources_sha256': {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
        'collection_review': [
            'Fresh namespace and per-case sandbox issues preserve earlier evidence; neutralisation is reproduced from original opening inputs.',
            'Replay collector separates any non-success conclusion into failures/ with scored=false; empty actions on failed execution must not be scored as a successful noop.',
            'Run-list association does not expose dispatch issue input; independent review must verify prepared issue and prompt/run evidence, and retain this association limitation.',
            'Replay KEEP_LOGS is intentionally incomplete for spend inspection; complete native artifacts and workflow logs must be audited for agent and detector usage.',
            'Complete-artifact collector rejects unfinished/wrong-head runs, expired artifacts, unsafe artifact names, and incomplete artifact pagination; its initial directory write prevents overwriting previous bundles.',
            'Collector jobs endpoint is not paginated; verify total_count equals collected jobs count on each completed run.',
            'Timeline outcomes span the fresh issue history; independently compare bot events with native requests, final state, timestamps and run link.'
        ],
        'cost_review': [
            'The sealed $0.50 completed-run and $2 cumulative estimate thresholds are coordinator stop rules between sequential runs; run.py does not automatically enforce budget, case order, prior-result stop or automatic-trigger inspection.',
            'Workflow source has agent 8-minute/30-turn/100-credit limits and a daily 1500-credit configuration; detector has its separate 10-minute/default-400-credit limit plus potential admission allocation.',
            'Configured credit and timeout guards do not demonstrate hard USD invoice enforcement; observed enforcement status requires native proxy policy and logs.',
            'Agent session total_cost_usd alone excludes detector. Native usage missing fields or parser zeroes must not silently become observed zero provider spend.',
            'If a component provably skipped before inference, report the skip; if usage is unavailable on an executed component, report unknown and stop further paid runs.',
            'Report available estimates by component with source/provenance; do not claim an invoice total or change the frozen runtime during this attempt.'
        ],
        'pending': 'Completed-run native evidence and independent scoring, if execution succeeds.'
    }
    with destination.open('x') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'output': str(destination), 'checks': len(checks), 'all_checks_passed': result['all_checks_passed']}, indent=2))

if __name__ == '__main__':
    main()
