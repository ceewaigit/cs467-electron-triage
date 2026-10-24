#!/usr/bin/env python3
"""Local independent checks of the read-only coordinator accounting helper."""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ATTEMPT=HERE.parent
helper=ATTEMPT/'check_cost.py'
namespace={'__name__':'independent_cost_helper','__file__':str(helper)}
exec(compile(helper.read_text(),str(helper),'exec'),namespace)
artifacts=ATTEMPT/'runs/40069225337/artifacts'
results=[]
original_jsonl=namespace['jsonl']

def trial(name,phase,rows,should_reject,tracker_transform=None):
    def read_rows(path):
        data=original_jsonl(path)
        return tracker_transform(data) if tracker_transform and path.name=='token-tracker-audit.jsonl' else data
    namespace['jsonl']=read_rows
    try:
        dollars=namespace['reconcile_phase'](artifacts,phase,rows,'claude-sonnet-5-5')
    except SystemExit as error:
        results.append({'name':name,'phase':phase,'rejected':True,'expected_rejection':should_reject,'pass':should_reject,'reason':str(error)})
    else:
        results.append({'name':name,'phase':phase,'rejected':False,'expected_rejection':should_reject,'pass':not should_reject,'estimate_usd':str(dollars)})
    finally: namespace['jsonl']=original_jsonl

for phase in ['agent','detection']:
    rows=original_jsonl(artifacts/'usage'/phase/'token_usage.jsonl')
    trial('intact native evidence',phase,rows,False)
    trial('missing first usage record',phase,rows[1:],True)
    trial('empty usage records',phase,[],True)
    bad=copy.deepcopy(rows);bad[0]['input_tokens']+=1
    trial('usage token mismatch',phase,bad,True)
    bad=copy.deepcopy(rows);bad[0]['ai_credits_this_response']+=1
    trial('credit rate mismatch',phase,bad,True)
    trial('missing tracker end',phase,rows,True,lambda xs:[x for i,x in enumerate(xs) if i!=next(i for i,x in enumerate(xs) if x['event']=='TRACK_END')])
    trial('duplicate tracker record',phase,rows,True,lambda xs:xs+[copy.deepcopy(xs[0])])
    def fail_message(xs):
        xs=copy.deepcopy(xs)
        next(x for x in xs if x['event']=='TRACK_START' and '/messages' in x['path'])['status']=400
        return xs
    trial('failed message status',phase,rows,True,fail_message)

result={'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),
        'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'tests':results,'all_passed':all(x['pass'] for x in results),
        'assessment':'Reconciliation closes the previously identified omission/truncation gap. Both phases are rate-recomputed and tied to complete message tracker IDs; detector summary is checked. Prior totals and thresholds remain coordinator checks between runs, not automatic dispatch enforcement or invoice limits.',
        'limits':['The helper checks native usage evidence rather than provider billing records.','Hard exhaustion enforcement is not exercised by these offline checks.','The updated helper was introduced after the first run, with original first checkpoint retained.']}
with (HERE/'independent-cost-helper-results.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'checks':len(results),'all_passed':result['all_passed']},indent=2))
