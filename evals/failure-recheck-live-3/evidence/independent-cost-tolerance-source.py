#!/usr/bin/env python3
"""Audit the narrow accounting-tolerance amendment with local source only."""
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
before_path=HERE/'check_cost-before-float-tolerance.py'
after_path=HERE.parent/'check_cost.py'
before=ast.parse(before_path.read_text())
after=ast.parse(after_path.read_text())
def function(tree,name):return next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
def assignment(tree,name):
    return next(x for x in function(tree,'main').body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets))
checks={
    'reconcile_phase_unchanged':ast.dump(function(before,'reconcile_phase'))==ast.dump(function(after,'reconcile_phase')),
    'within_budget_expression_unchanged':ast.dump(assignment(before,'within_budget'))==ast.dump(assignment(after,'within_budget')),
    'total_expression_unchanged':ast.dump(assignment(before,'total'))==ast.dump(assignment(after,'total')),
}
namespace={'__name__':'independent_cost_tolerance','__file__':str(after_path)}
exec(compile(after_path.read_text(),str(after_path),'exec'),namespace)
nodes=[]
for node in function(after,'main').body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['native_agent_cost','native_difference'] for t in node.targets):nodes.append(node)
    elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='require' and any(isinstance(child,ast.Name) and child.id=='native_difference' for child in ast.walk(node)):
        nodes.append(node)
module=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
trial_results=[]
for name,delta,accepted in [('exact','0',True),('observed rounding','-3e-17',True),('tolerance boundary','1e-12',True),('above tolerance','1.00001e-12',False),('one cheapest token','1e-7',False)]:
    scope=dict(namespace)
    scope['sessions']=[{'total_cost_usd':Decimal('0.1379387')+Decimal(delta)}]
    scope['phases']={'agent':{'recorded_usd_estimate':'0.1379387'}}
    try:exec(compile(module,str(after_path),'exec'),scope)
    except SystemExit:observed=False
    else:observed=True
    trial_results.append({'name':name,'delta_usd':delta,'accepted':observed,'expected_acceptance':accepted,'pass':observed==accepted})
checks['only_three_numeric_guard_nodes_extracted']=len(nodes)==3
checks['numeric_guard_cases_passed']=all(x['pass'] for x in trial_results)
result={'checks':checks,'all_passed':all(checks.values()),'trials':trial_results,'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [before_path,after_path,Path(__file__)]},'assessment':'This amendment resolves representation noise while retaining phase reconciliation, spend arithmetic, and threshold conditions. It does not turn an unknown/missing usage component into zero or a successful case.'}
with (HERE/'independent-cost-tolerance-results.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'all_passed':result['all_passed'],'checks':checks},indent=2))
