"""One frozen serial validation run; reuse the application's actual free runtime."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import httpx
import logistics_recovery.evaluation as evaluation
from logistics_recovery.config import Settings
from logistics_recovery.evaluation import evaluate_case, load_scenarios, summarize
from logistics_recovery.free_billing import BillingPause
from logistics_recovery.live import FreeLiveModel, FREE_MODEL, safe_pause_reason
from logistics_recovery.workflow import Workflow

os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
REPO = Path(__file__).resolve().parents[1]
MAX_REQUESTS = 72
AUDIT = {}
TOOLS = {'get_order', 'get_couriers', 'get_quotes', 'get_policy', 'get_events', 'propose_recovery', 'escalate'}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)


class ObservedWorkflow(Workflow):
    def start(self, incident_id):
        self.incident_id = incident_id
        return super().start(incident_id)

    def close(self):
        if hasattr(self, 'incident_id'):
            incident = self.incident_id
            assignment = self.repository.assignment(incident)
            AUDIT.update(history=self.repository.history(incident),
                         snapshot_after=self.repository.snapshot(incident).model_dump(mode='json'),
                         assignment=assignment.model_dump(mode='json') if assignment else None,
                         stats=self.repository.stats(incident),
                         terminal=self.repository.terminal_status(incident))
        super().close()


class TraceTransport(httpx.BaseTransport):
    def __init__(self, delegate):
        self.delegate = delegate
        self.case_id = None
        self.trace = []

    def handle_request(self, request):
        started = now()
        response = self.delegate.handle_request(request)
        response.read()
        try:
            data = response.json()
        except ValueError:
            data = {}
        data = data if isinstance(data, dict) else {}
        choices = data.get('choices')
        choices = choices if isinstance(choices, list) else []
        choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        message = choice.get('message')
        message = message if isinstance(message, dict) else {}
        calls = message.get('tool_calls')
        calls = calls if isinstance(calls, list) else []
        names = [c['function'].get('name') for c in calls if isinstance(c, dict) and isinstance(c.get('function'), dict)]
        usage = data.get('usage')
        usage = usage if isinstance(usage, dict) else {}
        error = data.get('error')
        code = error.get('code') if isinstance(error, dict) else None
        row = {'request': len(self.trace) + 1, 'case_id': self.case_id,
               'started_at_utc': started, 'completed_at_utc': now(),
               'http_status': response.status_code, 'choices_count': len(choices),
               'has_error': bool(error), 'safe_error_code': code if type(code) is int and code in {400,401,402,403,404,408,429,500,502,503,504} else None,
               'finish_reason': choice.get('finish_reason'),
               'tool_names': [name if name in TOOLS else 'unlisted' for name in names],
               'usage': {field: usage.get(field) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cost')}}
        self.trace.append(row)
        print(json.dumps({'request': row['request'], 'case': self.case_id,
                          'http_status': row['http_status'], 'tools': row['tool_names'],
                          'cost': row['usage']['cost']}), flush=True)
        return response

    def close(self):
        self.delegate.close()


class BatchModel:
    def __init__(self, live, initial):
        self.live, self.initial = live, initial

    def next_turn(self, context, tools):
        if self.live.guard.state['requests'] - self.initial >= MAX_REQUESTS:
            raise BillingPause('batch_request_limit')
        return self.live.next_turn(context, tools)


def witnessed_path(case, evidence):
    history = evidence.get('history', [])
    replans = [i for i, e in enumerate(history) if e['kind'] == 'replanning_required']
    created = [e['payload'] for e in history if e['kind'] == 'proposal_created']
    approved = [e['payload'] for e in history if e['kind'] == 'proposal_approved']
    escalation = next((e['payload'].get('detail') for e in reversed(history) if e['kind'] == 'case_escalated'), None)
    native = any(e['kind'] == 'model_turn' and e['payload']['kind'] == 'escalate' for e in history)
    assignment = evidence.get('assignment')
    fresh_approval = None
    if replans and assignment:
        later = history[replans[-1]+1:]
        fresh_ids = {e['payload']['proposal_id'] for e in later if e['kind'] == 'proposal_created'}
        approval_ids = {e['payload']['proposal_id'] for e in later if e['kind'] == 'proposal_approved'}
        fresh_approval = assignment['proposal_id'] in fresh_ids & approval_ids
    return {'proposal_count': len(created), 'approval_count': len(approved),
            'first_quote_id': created[0]['quote_id'] if created else None,
            'replanning_events': len(replans), 'fresh_approval_after_replan': fresh_approval,
            'changes_applied': bool(case.changes and approved),
            'accepted_native_escalation': native, 'escalation_detail': escalation,
            'escalation_source': ('native_model' if native else 'application') if escalation is not None else None,
            'model_error_codes': [e['payload']['code'] for e in history if e['kind'] == 'model_error'],
            'rejected_proposals': [e['payload'] for e in history if e['kind'] == 'proposal_invalid']}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Evidence exists; do not overwrite or silently repeat')
    args.output.mkdir(parents=True, mode=0o700)
    fixtures = REPO / 'fixtures/final-reserved'
    cases = load_scenarios(fixtures)
    manifest = json.loads((fixtures/'manifest.json').read_text())
    assert len(cases) == 12 and [c.id for c in cases] == manifest['case_order']
    for mode in ('baseline', 'replay'):
        report = json.loads((REPO/f'docs/evidence/final-reserved-{mode}.json').read_text())
        assert report['manifest'] == manifest and report['summary']['safe_case_successes'] == 12
    source = REPO/'src/logistics_recovery'
    files = sorted([*source.glob('*.py'), *source.joinpath('templates').glob('*.html')])
    digest = hashlib.sha256(b''.join(p.relative_to(source).as_posix().encode()+p.read_bytes() for p in files)).hexdigest()
    build = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    ledger_before = json.loads(args.ledger.read_text())
    assert ledger_before['status'] == 'active' and ledger_before['requests']+MAX_REQUESTS <= 1000
    save(args.output/'ledger-before.json', ledger_before)
    plan = {'started_at_utc': now(), 'build_ref': build, 'source_and_templates_sha256': digest,
            'manifest': manifest, 'case_order': [c.id for c in cases],
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'session_requests_before': ledger_before['requests'],
            'model_config': {'model_id': FREE_MODEL, 'tool_choice': 'required', 'reasoning_enabled': False,
                             'max_output_tokens': 600, 'max_attempts': 6, 'max_drafts': 3,
                             'maximum_new_requests': MAX_REQUESTS, 'session_request_limit': 1000,
                             'provider_max_price': {'prompt':0,'completion':0,'request':0},
                             'allow_fallbacks': False, 'require_parameters': True,
                             'pause_on_unknown_cost': False, 'runtime': 'FreeLiveModel'}}
    save(args.output/'plan.json', plan)
    results, observations = [], []
    active, pause, unexpected, safety = None, None, None, None
    before = after = None
    evaluation.Workflow = ObservedWorkflow
    with TemporaryDirectory() as runtime:
        settings = Settings(data_dir=Path(runtime), dispatcher_username='dispatcher',
                            dispatcher_password='private-validation-only', mode='live',
                            provider_key=args.key_file.read_text().strip(), model_id=FREE_MODEL,
                            billing_state_path=args.ledger)
        live = FreeLiveModel(settings)
        trace = TraceTransport(live.delegate)
        live.delegate = trace
        if live.guard:
            live.guard.transport = trace
        try:
            if live.status()['paused']:
                raise BillingPause(live.status()['reason'])
            live._verify_profile()
            before = live._billing()
            key = live._get('key', authenticated=True)
            if before.key_usage or before.account_usage:
                live.guard._pause('billed_usage_present')
            if before.free_remaining < MAX_REQUESTS:
                raise BillingPause('insufficient_batch_quota')
            save(args.output/'preflight.json', {'checked_at_utc': now(), 'profile_verified': live.profile_verified,
                 'billing': before.safe_dict(), 'key_limit': key['limit'], 'key_limit_reset': key['limit_reset'],
                 'provider_daily_limit': key['free_model_daily_requests']['limit']})
            model = BatchModel(live, ledger_before['requests'])
            for case in cases:
                active = case.id
                trace.case_id = case.id
                AUDIT.clear()
                start = len(trace.trace)
                case_before = live._billing()
                result = evaluate_case(case, 'live', model)
                case_after = live._billing()
                results.append(result)
                observation = {'case': result.model_dump(mode='json'), 'checked_at_utc': now(),
                               'provider_trace': trace.trace[start:], 'business_evidence': dict(AUDIT),
                               'witnessed_path': witnessed_path(case, AUDIT),
                               'billing_before': case_before.safe_dict(), 'billing_after': case_after.safe_dict()}
                observations.append(observation)
                save(args.output/(case.id+'.json'), observation)
                print(json.dumps({'completed_case':case.id,'passed':result.passed,'outcome':result.actual_outcome,
                                  'requests':len(trace.trace)-start,'completed':len(results),
                                  'native_escalation':observation['witnessed_path']['accepted_native_escalation']}),flush=True)
                if case_after.key_usage > case_before.key_usage or case_after.account_usage > case_before.account_usage:
                    live.guard._pause('billing_increase')
                if case_after.credits < case_before.credits:
                    live.guard._pause('credit_balance_decreased')
                if result.constraint_violations or result.unauthorized_commits or result.duplicates:
                    safety = 'business_safety_failure'
                    break
                if observation['witnessed_path']['fresh_approval_after_replan'] is False:
                    safety = 'replan_approval_failure'
                    break
        except BillingPause as error:
            pause = error.reason
            save(args.output/'pause.json', {'checked_at_utc':now(),'reason':pause,'active_case_id':active,
                                          'trace':trace.trace,'ungraded_business_evidence':dict(AUDIT)})
        except Exception as error:
            unexpected = type(error).__name__
            save(args.output/'unexpected-stop.json', {'checked_at_utc':now(),'error_type':unexpected,
                        'active_case_id':active,'trace':trace.trace,'ungraded_business_evidence':dict(AUDIT)})
        finally:
            try:
                closing = live._billing()
                after = closing.safe_dict()
                key = live._get('key', authenticated=True)
                closing_key = {name:key[name] for name in ('usage','limit','limit_reset','free_model_daily_requests')}
                if before and (closing.key_usage>before.key_usage or closing.account_usage>before.account_usage or closing.credits<before.credits):
                    if not pause:
                        pause='closing_billing_change'
                        try: live.guard._pause('billing_increase')
                        except BillingPause: pass
            except Exception:
                closing_key = None
                pause = pause or 'closing_billing_unverified'
            live.close()
    ledger_after = json.loads(args.ledger.read_text())
    events = ledger_after['events'][len(ledger_before['events']):]
    report = {**plan, 'completed_at_utc':now(), 'status':'paused' if pause else 'unexpected_stop' if unexpected else 'stopped_for_safety' if safety else 'completed',
              'pause_reason':pause,'unexpected_error_type':unexpected,'safety_stop':safety,
              'interrupted_case_id':active if active not in {r.case_id for r in results} else None,
              'summary':summarize(results),'cases':[r.model_dump(mode='json')for r in results],
              'observations':observations,'provider_trace':trace.trace,
              'new_request_attempts':ledger_after['requests']-ledger_before['requests'],
              'response_count':len(events),'zero_cost_receipts':sum(e['reported_cost_usd']=='0'for e in events),
              'unknown_cost_receipts':sum(e['reported_cost_usd']is None for e in events),
              'response_receipt_cost_usd': None if any(e['reported_cost_usd']is None for e in events)else str(sum(float(e['reported_cost_usd'])for e in events)),
              'billing_before':before.safe_dict()if before else None,'billing_after':after,'closing_key':closing_key,
              'session_requests_after':ledger_after['requests'],'ledger_status':ledger_after['status'],
              'limitations':['12 small fresh project-reserved parameter variants, not broad generalization or real company traffic.',
                             'Approvals and bookings simulated; failures deliberately injected by evaluator.',
                             'Outcome matches do not by themselves establish witnessed changed-state/negative-control paths.',
                             'Accepted native escalation distinguished from application budget stops.',
                             'Missing response costs remain unknown; account observations exclude purchase fees/coding-assistant usage.',
                             'No source/prompt/model tuning or repeated cases for a better result.']}
    save(args.output/'summary.json', report)
    print(json.dumps({k:report[k]for k in ('status','pause_reason','unexpected_error_type','safety_stop','new_request_attempts','summary','billing_after','session_requests_after')},indent=2),flush=True)
    if pause or unexpected or safety:
        sys.exit(2)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'setup_error_type':type(error).__name__}),flush=True)
        sys.exit(1)
