#!/usr/bin/env python3
"""Independently replay saved completed-run evidence without network/provider access.

Writes new per-case JSON audit outputs only in this evidence directory. Does not read
coordinator summaries. Frozen scorer is called in memory, never via its output CLI.
"""
import argparse
import datetime as dt
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE.parent
ROOT = ATTEMPT.parents[1]

def read(p):
    return json.loads(p.read_text())

def lines(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_new(p, value):
    with p.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')

def contents(row):
    c = row.get('message', {}).get('content', [])
    return c if isinstance(c, list) else []

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    m = read(ATTEMPT/'manifest.json')
    if args.case not in m['cases_in_order']:
        raise SystemExit('Unknown case.')
    destination = HERE/f'independent-{args.case}-results.json'
    normalized_path = HERE/f'independent-{args.case}-normalized-input.json'
    if destination.exists() or normalized_path.exists():
        raise SystemExit('Refusing to overwrite first independent case audit.')
    maps = read(ATTEMPT/'replay'/f"runs-{m['variant']}.json")
    found = [(issue,row) for issue,row in maps.items() if row['case']==args.case]
    if len(found)!=1: raise SystemExit('Expected one dispatched case.')
    issue_number, mapping = found[0]
    issue_number = int(issue_number)
    run_id = mapping['run_id']
    bundle = ATTEMPT/'runs'/str(run_id)
    artifact = bundle/'artifacts'
    run, jobs, artifacts = [read(bundle/f'{x}-completed.json') for x in ['run','jobs','artifacts']]
    original = read(ATTEMPT/'cases'/args.case/'input.json')
    expected = read(ATTEMPT/'cases'/args.case/'expected.json')
    case_map = read(ATTEMPT/'replay'/f"issues-{m['variant']}.json")[args.case]
    after = read(bundle/'issue-after-run.json')
    timeline = [e for page in read(bundle/'issue-timeline-pages.json') for e in page]
    success = run['conclusion']=='success'
    actual_path = ATTEMPT/'cases'/args.case/'actual'/m['variant']
    actual_path = actual_path/('run-1.json' if success else 'failures/run-1.json')
    actual = read(actual_path)
    workflow = (bundle/'workflow.log').read_text()
    checks = {
        'completed': run['status']=='completed',
        'source': run['head_sha']==m['source_commit']==mapping['head_sha']==actual['head_sha'],
        'event': run['event']=='workflow_dispatch',
        'run_association': run['id']==run_id==actual['run_id'],
        'issue_association': after['number']==issue_number==actual['issue'],
        'run_attempt_one': run['run_attempt']==1,
        'jobs_complete': jobs['total_count']==len(jobs['jobs']),
        'artifact_list_complete': artifacts['total_count']==len(artifacts['artifacts']),
        'artifact_directories_complete': all((artifact/x['name']).is_dir() and not x['expired'] for x in artifacts['artifacts']),
        'case_input_hash': sha(ATTEMPT/'cases'/args.case/'input.json')==m['case_sha256'][args.case]['input.json'],
        'case_expected_hash': sha(ATTEMPT/'cases'/args.case/'expected.json')==m['case_sha256'][args.case]['expected.json'],
        'scorer_hash': sha(ROOT/'evals/tools/score.py')==m['scorer_sha256'],
    }
    normalized = {'number':issue_number,'title':case_map['title'],'body':case_map['body'],
                  'labels':case_map['labels_at_open'],'state':'open',
                  'author_association':original['author_association'],'as_of':original['as_of'],'replay':True}
    session_path = artifact/'agent/agent-session.jsonl'
    session = lines(session_path) if session_path.exists() else []
    calls, replies, issue_reads, observed_reports = [], {}, [], []
    for index,row in enumerate(session):
        for c in contents(row):
            if c.get('type')=='tool_use':
                calls.append({'index':index,'id':c['id'],'name':c['name'],'input':c['input']})
            if c.get('type')=='tool_result':
                replies[c['tool_use_id']] = {'index':index,'content':c.get('content'),'is_error':c.get('is_error',False)}
                text = c.get('content')
                if isinstance(text,str) and text.startswith('[issue-triage/triage_checks v2] ok\n'):
                    observed_reports.append(json.loads(text.split('\n',1)[1]))
    for call in calls:
        if call['name']=='Read' and call['input'].get('file_path','').endswith('/.triage/issue.json'):
            reply = replies.get(call['id'],{}).get('content')
            if isinstance(reply,str):
                issue_reads.append(json.loads(re.sub(r'^\d+\t','',reply,flags=re.M)))
    if issue_reads: checks['prepared_issue_matches'] = all(x==normalized for x in issue_reads)
    checks['workflow_issue_preparation'] = f"saved issue #{issue_number} ({normalized['author_association']}, as of {normalized['as_of']}, {len(normalized['labels'])} labels)" in workflow
    observed_actions = {'labels_added':[], 'comment':None, 'other_writes':[]}
    comments, bot_events = [], []
    for event in timeline:
        actor = (event.get('actor') or event.get('user') or {}).get('login')
        kind = event.get('event')
        if actor=='github-actions[bot]':
            bot_events.append({k:event.get(k) for k in ['event','created_at','id']})
            if kind=='labeled': observed_actions['labels_added'].append(event['label']['name'])
            elif kind=='commented': comments.append(event['body'])
            else: observed_actions['other_writes'].append(f'{kind} by github-actions[bot]')
        elif kind=='labeled' and event['label']['name'] in normalized['labels']:
            continue
        elif kind not in ['labeled','commented','cross-referenced','mentioned','subscribed']:
            observed_actions['other_writes'].append(f'{kind} by {actor}')
    if comments: observed_actions['comment']=comments[-1]
    if len(comments)>1: observed_actions['other_writes'].append(f'{len(comments)} comments')
    if after['state']!='open': observed_actions['other_writes'].append(f"issue state {after['state']}")
    checks['timeline_export_matches'] = all(actual.get(k)==v for k,v in observed_actions.items())
    checks['final_labels_match'] = set(x['name'] for x in after['labels'])==set(normalized['labels'])|set(observed_actions['labels_added'])
    checks['at_most_one_comment'] = len(comments)<=1
    checks['comment_run_link'] = all(f'/actions/runs/{run_id}' in c for c in comments)
    checks['bot_writes_after_run_start'] = all(not e['created_at'] or e['created_at']>=run['run_started_at'] for e in bot_events)
    namespace = {'__file__':str(ROOT/'evals/tools/score.py'),'__name__':'independent_frozen_scoring'}
    exec(compile((ROOT/'evals/tools/score.py').read_text(), namespace['__file__'], 'exec'),namespace)
    score = namespace['score_run'](expected,observed_actions) if success else None
    if not success: checks['failure_excluded'] = actual.get('scored') is False
    native_path = artifact/'agent/agent_output.json'
    native = read(native_path) if native_path.exists() else {'items':[]}
    label_requests = [x for x in native['items'] if x['type']=='add_labels']
    comment_requests = [x for x in native['items'] if x['type']=='triage_comment']
    if success:
        checks['native_label_targets'] = all(int(x.get('item_number',issue_number))==issue_number for x in label_requests)
        checks['native_label_actions_match'] = sorted(l for x in label_requests for l in x['labels'])==sorted(observed_actions['labels_added'])
        checks['native_outputs_allowlisted'] = all(x['type'] in ['add_labels','triage_comment','noop'] for x in native['items'])
        checks['native_output_counts'] = len(label_requests)<=1 and len(comment_requests)<=1
    # Invoke only known local helper paths with structured arguments and a minimal env.
    # Neither helper contacts GitHub or a model provider.
    write_new(normalized_path,normalized)
    env = {'PATH':os.environ.get('PATH','/usr/bin:/bin'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
    helper_root = ROOT/'.claude/skills/issue-triage/scripts'
    proc = subprocess.run(['python3',str(helper_root/'triage_checks.py'),str(normalized_path)],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
    replay_report = json.loads(proc.stdout.split('\n',1)[1])
    checks['deterministic_report_replay'] = bool(observed_reports) and all(x==replay_report for x in observed_reports)
    helper_replays = [{'helper':'triage_checks.py','returncode':proc.returncode,'stdout_sha256':hashlib.sha256(proc.stdout.encode()).hexdigest()}]
    for request in label_requests:
        p=subprocess.run(['python3',str(helper_root/'check_labels.py'),*request['labels']],cwd=ROOT,env=env,capture_output=True,text=True)
        checks['label_helper_replay'] = p.returncode==0
        helper_replays.append({'helper':'check_labels.py','returncode':p.returncode,'stdout':p.stdout})
    for request in comment_requests:
        argv=['python3',str(helper_root/'render_comment.py'),'--kinds',request['kinds']]
        if request.get('refs'): argv += ['--refs',str(request['refs'])]
        p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True)
        rendered=p.stdout.split('-----BEGIN COMMENT-----\n',1)[-1].split('\n-----END COMMENT-----',1)[0]
        checks['comment_helper_replay']=p.returncode==0 and bool(comments) and comments[0].startswith(rendered+'\n')
        helper_replays.append({'helper':'render_comment.py','returncode':p.returncode,'stdout':p.stdout})
    # Confirm checks and corresponding validators completed before proposed writes.
    first_write=min([c['index'] for c in calls if c['name'] in ['mcp__safeoutputs__add_labels','mcp__safeoutputs__triage_comment','mcp__safeoutputs__noop']],default=len(session))
    def successful_marker(marker,before):
        return any(r['index']<before and not r['is_error'] and isinstance(r['content'],str) and marker in r['content'] for r in replies.values())
    if success:
        checks['checks_before_output']=successful_marker('[issue-triage/triage_checks v2] ok',first_write)
        if label_requests: checks['labels_validated_before_output']=successful_marker('[issue-triage/check_labels v1] ok',first_write)
        if comment_requests: checks['comment_validated_before_output']=successful_marker('[issue-triage/render_comment v3] ok',first_write)
    cost_components={}
    for phase,usage_name in [('agent','agent_usage.json'),('detection','detection_usage.json')]:
        base=artifact/phase
        token_path=base/'sandbox/firewall/logs/api-proxy-logs/token-usage.jsonl'
        config_path=base/'sandbox/firewall/audit/awf-resolved-config.json'
        summary_path=base/usage_name
        if not all(p.exists() for p in [token_path,config_path,summary_path]):
            cost_components[phase]={'status':'missing_or_skipped','estimate_usd':None}
            continue
        token_rows=lines(token_path)
        config, summary=read(config_path),read(summary_path)
        tracker=lines(base/'sandbox/firewall/logs/api-proxy-logs/token-tracker-audit.jsonl')
        starts={r['rid']:r for r in tracker if r['event']=='TRACK_START'}
        ends={r['rid']:r for r in tracker if r['event']=='TRACK_END'}
        message_ids={rid for rid,r in starts.items() if '/messages' in r['path']}
        checks[f'{phase}_message_usage_complete']=message_ids==set(r['request_id'] for r in token_rows) and all(ends.get(rid,{}).get('result')=='ok' for rid in message_ids)
        checks[f'{phase}_usage_observed']=bool(token_rows)
        checks[f'{phase}_usage_success_model']=all(r['status']==200 and r['model']==m['model'] for r in token_rows)
        token_sums={k:sum(r[k] for r in token_rows) for k in ['input_tokens','output_tokens','cache_read_tokens','cache_write_tokens']}
        checks[f'{phase}_usage_summary_matches']=all(summary[k]==v for k,v in token_sums.items())
        rate_map={'input_tokens':'input','output_tokens':'output','cache_read_tokens':'cache_read','cache_write_tokens':'cache_write'}
        estimate=Decimal(0)
        for row in token_rows:
            rates=config['apiProxyProviders'][row['provider']]['models'][row['model']]['cost']
            estimate+=sum(Decimal(row[k])*Decimal(rates[v]) for k,v in rate_map.items())
        credits=sum(Decimal(str(r['ai_credits_this_response'])) for r in token_rows)
        checks[f'{phase}_credit_summary_matches']=credits==Decimal(str(summary['ai_credits']))
        checks[f'{phase}_proxy_enabled']=config['enableApiProxy'] is True
        checks[f'{phase}_configured_credit_limit']=config['maxAiCredits']==(100 if phase=='agent' else 400)
        checks[f'{phase}_usage_copies_match']=token_path.read_bytes()==(artifact/'usage'/phase/'token_usage.jsonl').read_bytes()
        cost_components[phase]={'status':'observed_nonzero_usage','requests':len(token_rows),'token_totals':token_sums,'ai_credits':float(credits),'estimate_usd':float(estimate),'rates':config['apiProxyProviders']['anthropic']['models'][m['model']]['cost'],'pricing_source':sorted({r['ai_credits_pricing_source'] for r in token_rows}),'configured_max_ai_credits':config['maxAiCredits'],'configured_timeout_minutes':config['agentTimeout'],'non_message_no_usage':[{ 'path':starts[rid]['path'],'result':end['result']} for rid,end in ends.items() if end['result']=='no_usage' and rid in starts and rid not in message_ids],'invoice_total':None}
    session_results=[r for r in session if r['type'] in ['result','session.result']]
    agent_result=session_results[-1] if session_results else None
    if agent_result:
        checks['agent_completed_without_error']=agent_result.get('is_error') is False and agent_result.get('subtype')=='success'
        checks['agent_session_estimate_matches']=Decimal(str(agent_result['total_cost_usd']))==Decimal(str(cost_components['agent']['estimate_usd']))
    detector_path=artifact/'detection/detection_result.json'
    detector=read(detector_path) if detector_path.exists() else None
    if success: checks['detector_no_threats']=detector is not None and all(detector.get(k) is False for k in ['prompt_injection','secret_leak','malicious_patch'])
    estimates=[x['estimate_usd'] for x in cost_components.values()]
    combined=float(sum(Decimal(str(x)) for x in estimates)) if all(x is not None for x in estimates) else None
    important_files=[f for f in bundle.rglob('*') if f.is_file()]+[actual_path,ATTEMPT/'cases'/args.case/'expected.json',ATTEMPT/'manifest.json',ATTEMPT/'PROTOCOL.md',ATTEMPT/'budget-stop-rule.json',ROOT/'evals/tools/score.py',Path(__file__),normalized_path]
    result={
        'reviewed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'independence':'Inspected native source evidence and scored without reading coordinator scores or conclusions.',
        'case':args.case,'run_id':run_id,'issue':issue_number,'source_commit':m['source_commit'],
        'execution_conclusion':run['conclusion'],'scorable':success,'independent_frozen_score':score,
        'checks':checks,'all_integrity_and_procedure_checks_passed':all(checks.values()),
        'observed_actions':observed_actions,'native_requests':native,'bot_events':bot_events,
        'tools':[{'index':c['index'],'name':c['name'],'input':c['input']} for c in calls],
        'helper_replays':helper_replays,'deterministic_report':replay_report,
        'agent_session_result':{k:agent_result.get(k) for k in ['subtype','is_error','num_turns','total_cost_usd','permission_denials','terminal_reason']} if agent_result else None,
        'detection_result':detector,'cost_components':cost_components,
        'combined_rate_derived_estimate_usd':combined,'below_completed_run_stop_threshold':combined is not None and combined<=read(ATTEMPT/'budget-stop-rule.json')['maximum_completed_run_estimate_before_continuing_usd'],
        'hard_enforcement_assessment':'Proxy enabled, configured component credit/time limits and request accounting are visible. This low-usage run did not exercise an exhausted credit/time budget. It does not prove a hard USD invoice cap; the sealed USD thresholds are coordinator checks between runs.',
        'limits':['Targeted known-failure sample, one repeat; no population or pass-cubed claim.','No cross-run invoice claim; duplicated artifact copies were compared, not summed.','A failed execution is excluded from model correctness even if it has no writes.','Saved execution marker state started is startup evidence; success is established from session, workflow and observed writer outcomes.'],
        'sources_sha256':{str(p.relative_to(ROOT)):sha(p) for p in important_files}
    }
    write_new(destination,result)
    print(json.dumps({'output':str(destination),'score':score,'checks':len(checks),'failed_checks':[k for k,v in checks.items() if not v],'estimate_usd':combined},indent=2))

if __name__=='__main__': main()
