"""Validate HireGuard's canonical example payloads and OpenAPI JSON-schema references.
Run: pip install jsonschema PyYAML && python scripts/validate_contracts.py
"""
from __future__ import annotations
import json
from pathlib import Path
import warnings
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'contracts/schemas'; E=ROOT/'contracts/examples'
schemas={p.stem.replace('.schema',''): json.loads(p.read_text(encoding='utf-8')) for p in S.glob('*.schema.json')}
registry=Registry()
for name,data in schemas.items():
 Draft202012Validator.check_schema(data)
 registry=registry.with_resource(data['$id'], Resource.from_contents(data))
for name,data in schemas.items():
 f=E/(name+'.json')
 if not f.is_file():raise SystemExit(f'MISSING EXAMPLE: {name}')
 value=json.loads(f.read_text(encoding='utf-8'))
 validator=Draft202012Validator(data, registry=registry, format_checker=FormatChecker())
 errors=list(validator.iter_errors(value))
 if errors:raise SystemExit(f'{name}: '+ '; '.join(str(err) for err in errors))
api=yaml.safe_load((ROOT/'contracts/openapi.yaml').read_text(encoding='utf-8'))
assert api['openapi']=='3.1.0'
for path,methods in api['paths'].items():
 for method,op in methods.items():
  blocks=[op.get('requestBody',{})]+list(op.get('responses',{}).values())
  def walk(o):
   if isinstance(o,dict):
    for k,v in o.items():
     if k=='$ref':
      p=(ROOT/'contracts'/v).resolve()
      if not p.is_file():raise SystemExit(f'Bad OpenAPI $ref {v} at {path} {method}')
     else:walk(v)
   elif isinstance(o,list):
    for x in o:walk(x)
  for b in blocks:walk(b)
print(f'PASS: {len(schemas)} Draft-2020-12 schemas, {len(schemas)} primary examples, {len(api["paths"])} OpenAPI routes validated')

# Cross-fixture golden workflow: target -> checker -> machine proposal -> human review.
fixture=lambda name:json.loads((E/(name+'.json')).read_text(encoding='utf-8'))
turn=fixture('AdapterTurnResponse'); event=fixture('AuditEvent'); check=fixture('CheckResult'); finding=fixture('Finding'); review=fixture('ReviewReceipt'); scenario=fixture('Scenario'); rule=fixture('PolicyRule'); run=fixture('RunCreate'); detail=fixture('RunDetail')
assert run['scenario_id']==scenario['scenario_id']==finding['scenario_id']
assert finding['run_id']==check['run_id']==event['run_id']==detail['run_id']
assert turn['reply_text']==event['data']['target_response']
assert event['event_type']=='TURN' and check['turn_index']==finding['proposal']['turn_index']==event['turn_index']
assert rule['forbidden_value'] in turn['reply_text'] and rule['rule_id']==check['rule_id']==finding['rule_id']
assert event['event_id'] in check['evidence_event_ids'] and event['event_id'] in finding['proposal']['evidence_event_ids']
assert check['result']=='FAIL' and finding['proposal']['verdict']=='FAIL' and finding['reviewer_status']=='PENDING'
assert review['finding_id']==finding['finding_id'] and review['decision']=='CONFIRMED'
print('PASS: Golden cross-fixture link and canary chain are consistent')

for name in ['AuditEvent_STATE','AuditEvent_DECISION','AuditEvent_CHECK','AuditEvent_ERROR','NextProbe_STOP']:
 main=name.split('_')[0] if name.startswith('AuditEvent') else 'NextProbe'
 validator=Draft202012Validator(schemas[main], registry=registry, format_checker=FormatChecker())
 assert validator.is_valid(json.loads((E/(name+'.json')).read_text(encoding='utf-8'))), name
print('PASS: Additional typed event payload fixtures + STOP probe')

# Contract tool specs and mock target modes have their own validators.
from jsonschema import Draft202012Validator as V
tools_spec=json.loads((ROOT/'contracts/agent_tools.json').read_text(encoding='utf-8'))
assert [t['name'] for t in tools_spec['tools']]==['load_policy','send_turn','check_evidence']
for tool in tools_spec['tools']:
 V.check_schema(tool['arguments_schema'])
 assert tool['arguments_schema']['additionalProperties'] is False
mocks=json.loads((ROOT/'contracts/mock_target_modes.json').read_text(encoding='utf-8'))
for mode in ['refusal','canary_disclosure','scoring']:
 assert V(schemas['AdapterTurnResponse'],registry=registry).is_valid(mocks[mode]),mode
assert V(schemas['ErrorResponse'],registry=registry).is_valid(mocks['timeout'])
assert not V(schemas['AdapterTurnResponse'],registry=registry).is_valid(mocks['malformed'])
assert not V(schemas['NextProbe'],registry=registry).is_valid({'action':'STOP','strategy_id':'s','message':'illegal','observed_fact':'x','decision_reason':'x','hypothesis':'x'})
print('PASS: Agent tool allowlist and mock target modes including negative tests')
