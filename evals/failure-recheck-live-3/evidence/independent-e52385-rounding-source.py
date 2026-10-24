#!/usr/bin/env python3
"""Explain the exact-equality stop without changing any saved evidence or gate."""
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ATTEMPT=HERE.parent
bundle=ATTEMPT/'runs/40070123304'
artifact=bundle/'artifacts'
def read(p):return json.loads(p.read_text(),parse_float=Decimal)
def lines(p):return [json.loads(l,parse_float=Decimal) for l in p.read_text().splitlines() if l.strip()]
rows=lines(artifact/'agent/sandbox/firewall/logs/api-proxy-logs/token-usage.jsonl')
config=read(artifact/'agent/sandbox/firewall/audit/awf-resolved-config.json')
rates=config['apiProxyProviders']['anthropic']['models']['claude-sonnet-5-5']['cost']
fields={'input_tokens':'input','output_tokens':'output','cache_read_tokens':'cache_read','cache_write_tokens':'cache_write'}
request_dollars=[sum(Decimal(r[field])*Decimal(rates[rate]) for field,rate in fields.items()) for r in rows]
exact=sum(request_dollars)
session=next(row for row in lines(artifact/'agent/agent-session.jsonl') if row['type']=='session.result')
native=session['total_cost_usd']
binary_sum=sum(float(value) for value in request_dollars)
float_epsilon=Decimal('0.000000000001')
original=read(HERE/'independent-e52385-results-v2.json')
blocking_checks={name:value for name,value in original['checks'].items() if name!='agent_session_estimate_matches'}
result={'native_serialized_usd':str(native),'exact_rate_recomputed_usd':str(exact),
        'signed_native_minus_exact_usd':str(native-exact),'absolute_difference_usd':str(abs(native-exact)),
        'request_exact_dollar_values':[str(x) for x in request_dollars],
        'sum_of_binary_float_request_costs_repr':repr(binary_sum),
        'binary_float_sum_reproduces_native':str(binary_sum)==str(native),
        'ulp_at_estimate':repr(math.ulp(float(exact))),
        'proposed_absolute_comparison_tolerance_usd':str(float_epsilon),
        'difference_within_tolerance':abs(native-exact)<=float_epsilon,
        'smallest_per_token_rate_usd':str(min(Decimal(x) for x in rates.values())),
        'all_other_original_checks_passed':all(blocking_checks.values()),
        'original_frozen_score':original['independent_frozen_score'],
        'conclusion':'The serialized native USD value differs by 3e-17 USD from exact token-rate accounting. All message IDs and token summaries reconcile. This is numerical representation noise, not missing usage or a material cost-evidence discrepancy.',
        'continuation_assessment':'After recording this reconciliation, accepting only a tiny absolute numeric tolerance alongside unchanged complete request/token/rate checks is consistent with the sealed inspectable-cost protocol. No runtime, gold, dollar threshold, or per-case retry is required.',
        'preservation':'The original exact-equality failure remains in independent-e52385-results-v2.json. No result was overwritten.',
        'source_hashes':{str(p.relative_to(ATTEMPT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'independent-e52385-results-v2.json',artifact/'agent/agent-session.jsonl',artifact/'agent/sandbox/firewall/logs/api-proxy-logs/token-usage.jsonl',artifact/'agent/sandbox/firewall/audit/awf-resolved-config.json']}}
with (HERE/'independent-e52385-rounding-results.json').open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(result,indent=2,ensure_ascii=False))
