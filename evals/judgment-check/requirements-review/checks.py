#!/usr/bin/env python3
"""Read a committed archive and verify assignment evidence without network access."""
import argparse, collections, hashlib, importlib.util, json, pathlib, subprocess, sys
OUT=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--snapshot',type=pathlib.Path,required=True)
ROOT=parser.parse_args().snapshot.resolve()
REPO=OUT.parents[2]
COMMIT='90724fea4152861499063b4f163d84c28348b0d3'
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=REPO,text=True).strip()
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,ROOT/p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
results={'commit':COMMIT}
cases=ROOT/'evals/golden/cases'
inputs={p.parent.name:json.loads(p.read_text()) for p in cases.glob('*/input.json')}
expected={k:read(f'evals/golden/cases/{k}/expected.json') for k in inputs}
results['counts']={'cases':len(inputs),'sets':dict(collections.Counter(x['set'] for x in inputs.values())),'skip_cases':[k for k,v in expected.items() if v['decision']=='skip']}
freeze_paths=['evals/golden/RUBRIC.md','evals/tools/score.py']+[str(p.relative_to(ROOT)) for p in cases.glob('*/input.json')]+[str(p.relative_to(ROOT)) for p in cases.glob('*/expected.json')]
results['freeze']={'commit':git('rev-parse','4baa2cb'),'date':git('show','-s','--format=%cI','4baa2cb'),'files':len(freeze_paths),'changed':git('diff','--name-only','4baa2cb',COMMIT,'--',*freeze_paths).splitlines()}
source={x['number']:x for x in map(json.loads,(ROOT/'evals/data/electron_issues.jsonl').read_text().splitlines())}
fetch=module('fetch','evals/tools/fetch_issues.py')
raw={n['number']:n for p in (ROOT/'evals/data/raw').glob('*.json') for n in json.loads(p.read_text())['data']['search']['nodes'] if n}
checks={}
for k,v in inputs.items():
 if v['set']=='adversarial':continue
 n=int(k[1:]);s=source[n];rec=fetch.opening_state(raw[n])
 checks[k]={'raw_reconstruction_matches_clean_row':rec==s,'input_matches_row':all(v[x]==s[y] for x,y in [('title','title'),('body','body'),('labels_at_open','labels_at_open'),('author_association','author_association'),('as_of','created_at')]),'body_source':v['body_source'],'upstream':v['source']}
results['historical_input_reconstruction']=checks
for name,path,replace in [('current_live','evals/failure-recheck-live-3/manifest.json',False),('old_dry_run','evals/golden/results/assistant-dry-run/manifest.json',False),('reproduction_candidate','evals/reproduction-check/evidence/manifest.json',True)]:
 manifest=read(path);hashes=manifest['runtime_sha256'].copy()
 if replace:hashes['.claude/skills/issue-triage/SKILL.md']=read('evals/reproduction-check/protocol.json')['policy_sha256']['candidate']
 results[name+'_runtime']={'source':manifest['source_commit'],'files':len(hashes),'different_from_reviewed_commit':[p for p,h in hashes.items() if sha(p)!=h]}
score=module('frozen_score','evals/tools/score.py')
results['scores']={}
for variant in ['agent','final','assistant-dry-run','baseline-v2','obey']:
 rows=[]
 for k in inputs:
  for p in (cases/k/'actual'/variant).glob('run-*.json'):
   act=json.loads(p.read_text());rows.append({'case':k,'run':p.name,'set':inputs[k]['set'],**score.score_run(expected[k],act)})
 results['scores'][variant]={'runs':len(rows),'real_runs':sum(r['set']!='adversarial' for r in rows),'real_pass':sum(r['set']!='adversarial' and r['pass'] for r in rows),'adversarial_runs':sum(r['set']=='adversarial' for r in rows),'adversarial_pass':sum(r['set']=='adversarial' and r['pass'] for r in rows),'safety_failures':sum(r['safety'] for r in rows),'failures':[r for r in rows if not r['pass']]}
results['current_live_scores']=[]
for p in sorted((ROOT/'evals/failure-recheck-live-3/cases').glob('*/actual/failure-recheck-live-3/run-1.json')):
 k=p.parents[2].name;act=json.loads(p.read_text());results['current_live_scores'].append({'case':k,'run_id':act['run_id'],'head_sha':act['head_sha'],**score.score_run(expected[k],act)})
# Inspect original event records rather than accepting only the skill-check summary.
results['session_evidence']={}
for variant in ['agent','final']:
 rows=[];read_paths=collections.Counter();models=collections.Counter();times=[]
 for p in sorted(cases.glob(f'*/actual/{variant}/logs/run-*/agent-session.jsonl')):
  events=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
  tools=[];seen=set()
  for e in events:
   if e.get('timestamp'):times.append(e['timestamp'])
   if e.get('type')=='session.init':models[e.get('model')]+=1
   message=e.get('message',{})
   if not isinstance(message,dict):continue
   content=message.get('content',[])
   if not isinstance(content,list):continue
   for x in content:
    if not isinstance(x,dict) or x.get('type')!='tool_use' or x.get('id') in seen:continue
    seen.add(x.get('id'));tools.append(x)
    if x['name']=='Read':read_paths[x['input'].get('file_path','')]+=1
  rows.append({'case':p.parents[4].name,'run':p.parent.name,'skill_invoked':any(t['name']=='Skill' and t['input'].get('skill')=='issue-triage' for t in tools),'triage_checks_called':any(t['name']=='Bash' and 'triage_checks.py' in t['input'].get('command','') for t in tools)})
 results['session_evidence'][variant]={'runs':len(rows),'skill_invoked':sum(r['skill_invoked'] for r in rows),'triage_checks_called':sum(r['triage_checks_called'] for r in rows),'models':dict(models),'earliest_event':min(times),'read_paths':dict(read_paths)}
results['design']={'line_count':len((ROOT/'DESIGN.md').read_text().splitlines()),'max_line_length':max(map(len,(ROOT/'DESIGN.md').read_text().splitlines())),'final_line':(ROOT/'DESIGN.md').read_text().splitlines()[-1]}
results['bot_attribution']={}
for p in sorted((ROOT/'evals/failure-recheck-live-3/runs').glob('*/issue-timeline-pages.json')):
 data=json.loads(p.read_text()); found=[]
 def walk(x):
  if isinstance(x,dict):
   if x.get('event') in ['commented','labeled']:found.append({'event':x['event'],'actor':(x.get('actor') or {}).get('login'),'created_at':x.get('created_at')})
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(data);results['bot_attribution'][p.parent.name]=found
results['reproduction_candidate_policy_match']=sha('evals/reproduction-check/policies/candidate-SKILL.md')==sha('.claude/skills/issue-triage/SKILL.md')
# Independently inspect the five current hosted skill sessions.
current_sessions=[]
for p in sorted((ROOT/'evals/failure-recheck-live-3/cases').glob('*/actual/failure-recheck-live-3/logs/run-1/agent-session.jsonl')):
 events=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]; tool_calls=[]; seen=set(); models=set()
 for event in events:
  if event.get('type')=='session.init':models.add(event.get('model'))
  message=event.get('message',{})
  if not isinstance(message,dict) or not isinstance(message.get('content'),list):continue
  for part in message['content']:
   if not isinstance(part,dict) or part.get('type')!='tool_use' or part.get('id') in seen:continue
   seen.add(part.get('id'));tool_calls.append(part)
 text=p.read_text()
 current_sessions.append({'case':p.parents[4].name,'models':sorted(models),'skill_called':any(x['name']=='Skill' and x['input'].get('skill')=='issue-triage' for x in tool_calls),'triage_checks_called':any(x['name']=='Bash' and 'triage_checks.py' in x['input'].get('command','') for x in tool_calls),'skill_read_directly':any(x['name']=='Read' and x['input'].get('file_path','').endswith('/.claude/skills/issue-triage/SKILL.md') for x in tool_calls),'current_reproduction_instruction_visible':'A constructor call, options object, configuration fragment' in text})
results['current_hosted_skill_sessions']=current_sessions
# Verify fresh candidate exports, frozen sources and per-case scores directly.
exp_root=ROOT/'evals/reproduction-check'
manifest=read('evals/reproduction-check/evidence/manifest.json')
collection=read('evals/reproduction-check/evidence/collection.json')
export_hash_failures=[]
for decision, export in collection['exports'].items():
 for relative, digest in export['file_sha256'].items():
  if hashlib.sha256((exp_root/relative).read_bytes()).hexdigest()!=digest:export_hash_failures.append(relative)
freeze_failures=[]
for relative,digest in manifest['freeze_sha256'].items():
 if hashlib.sha256((exp_root/'evidence/frozen'/relative).read_bytes()).hexdigest()!=digest:freeze_failures.append(relative)
fresh=[]
for p in sorted((exp_root/'cases').glob('*/actual/candidate/run-*.json')):
 k=p.parents[2].name; exp=json.loads((exp_root/'cases'/k/'expected.json').read_text());act=json.loads(p.read_text())
 fresh.append({'case':k,'run':p.name,'historical':k.startswith('e'),**score.score_run(exp,act)})
results['fresh_candidate']={'cases':len({x['case'] for x in fresh}),'historical_cases':len({x['case'] for x in fresh if x['historical']}),'runs':len(fresh),'historical_passes':sum(x['pass'] and x['historical'] for x in fresh),'constructed_passes':sum(x['pass'] and not x['historical'] for x in fresh),'freeze_files':len(manifest['freeze_sha256']),'freeze_hash_failures':freeze_failures,'exported_decisions':len(collection['exports']),'export_hash_failures':export_hash_failures,'failures':[x for x in fresh if not x['pass']]}
(OUT/'direct-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:v for k,v in results.items() if k not in ['historical_input_reconstruction','scores','session_evidence','bot_attribution']},indent=2))
