// k6 load test for the two workflows (docs/team/PERFORMANCE.md).
//
// One iteration = one customer and one agent working one ticket end to end:
//   W1  GET the public submit form, POST it (CSRF token + cookie)  -> ticket Open
//   W2  agent lists open tickets, resolves the new ticket with a follow-up
//       through the API, then reads the ticket back and checks status = 3
//
// Run (two runs per load level, at least 60 s each):
//   k6 run -e VUS=1 -e RUN=1u_run1 tests/team/perf/helpdesk_load.js
//   k6 run -e VUS=5 -e RUN=5u_run1 tests/team/perf/helpdesk_load.js
//
// Targets (p95, from the test plan): reads < 500 ms, writes < 1500 ms,
// failed requests < 1 %, every functional check passes.
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import encoding from 'k6/encoding';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';
const VUS = parseInt(__ENV.VUS || '1', 10);
const DURATION = __ENV.DURATION || '75s';
const RUN = __ENV.RUN || `${VUS}u`;
const OUT = __ENV.OUT || 'docs/team/evidence/performance';
const AUTH = { Authorization: 'Basic ' + encoding.b64encode('alice:Pa33w0rd') };

export const options = {
  scenarios: {
    workflows: { executor: 'constant-vus', vus: VUS, duration: DURATION },
  },
  thresholds: {
    'http_req_duration{kind:read}': ['p(95)<500'],
    'http_req_duration{kind:write}': ['p(95)<1500'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate==1.0'],
    // per-endpoint breakdown (always true; makes k6 report each endpoint)
    'http_req_duration{name:GET submit form}': ['max>=0'],
    'http_req_duration{name:POST submit form}': ['max>=0'],
    'http_req_duration{name:GET open tickets}': ['max>=0'],
    'http_req_duration{name:POST follow-up resolve}': ['max>=0'],
    'http_req_duration{name:GET ticket read-back}': ['max>=0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

function csrfFrom(html) {
  const m = (html || '').match(/name="csrfmiddlewaretoken" value="([^"]+)"/);
  return m ? m[1] : '';
}

export default function () {
  let ticketId = null;

  group('W1 submit ticket (public form)', () => {
    const form = http.get(`${BASE}/tickets/submit/`, { tags: { kind: 'read', name: 'GET submit form' } });
    check(form, { 'form 200': (r) => r.status === 200 });
    const res = http.post(
      `${BASE}/tickets/submit/`,
      {
        csrfmiddlewaretoken: csrfFrom(form.body),
        queue: '3', // IT Support in the demo data
        title: `k6 ${RUN} vu${__VU} it${__ITER}`,
        body: 'Load test ticket',
        priority: '3',
        submitter_email: 'sam.rivera@example.com',
      },
      { headers: { Referer: `${BASE}/tickets/submit/` }, tags: { kind: 'write', name: 'POST submit form' } },
    );
    const m = (res.url || '').match(/ticket=[A-Za-z0-9]+-(\d+)/);
    ticketId = m ? m[1] : null;
    check(res, { 'W1 redirected to ticket page': () => ticketId !== null });
  });

  if (!ticketId) {
    sleep(1); // keep the think time when W1 fails (e.g. server down)
    return;
  }

  group('W2 resolve ticket (staff API)', () => {
    const list = http.get(`${BASE}/api/tickets/?status=1`, { headers: AUTH, tags: { kind: 'read', name: 'GET open tickets' } });
    check(list, { 'list 200': (r) => r.status === 200 });
    const fu = http.post(
      `${BASE}/api/followups/`,
      JSON.stringify({ ticket: Number(ticketId), comment: 'Resolved by k6', new_status: 3 }),
      { headers: Object.assign({ 'Content-Type': 'application/json' }, AUTH), tags: { kind: 'write', name: 'POST follow-up resolve' } },
    );
    check(fu, { 'follow-up 201': (r) => r.status === 201 });
    const back = http.get(`${BASE}/api/tickets/${ticketId}/`, { headers: AUTH, tags: { kind: 'read', name: 'GET ticket read-back' } });
    check(back, { 'read-back status Resolved': (r) => r.status === 200 && r.json('status') === 3 });
  });

  sleep(1); // think time
}

export function handleSummary(data) {
  const m = data.metrics;
  const p = (name) => (m[name] ? m[name].values : {});
  const line = (label, v) => `${label.padEnd(34)} avg ${(v.avg || 0).toFixed(0).padStart(6)} ms  p95 ${(v['p(95)'] || 0).toFixed(0).padStart(6)} ms  max ${(v.max || 0).toFixed(0).padStart(6)} ms`;
  const thresholds = Object.entries(m)
    .filter(([, v]) => v.thresholds)
    .map(([k, v]) => `${k}: ${Object.entries(v.thresholds).map(([t, r]) => `${t} ${r.ok ? 'PASS' : 'FAIL'}`).join(', ')}`);
  const text = [
    `run ${RUN}: ${VUS} virtual user(s), ${DURATION}`,
    `iterations ${p('iterations').count}  (${(p('iterations').rate || 0).toFixed(2)}/s)`,
    `requests ${p('http_reqs').count}  failed ${((p('http_req_failed').rate || 0) * 100).toFixed(2)} %  checks ${((p('checks').rate || 0) * 100).toFixed(2)} %`,
    line('all requests', p('http_req_duration')),
    line('reads', p('http_req_duration{kind:read}')),
    line('writes', p('http_req_duration{kind:write}')),
    ...['GET submit form', 'POST submit form', 'GET open tickets', 'POST follow-up resolve', 'GET ticket read-back']
      .map((n) => line(`  ${n}`, p(`http_req_duration{name:${n}}`))),
    ...thresholds.filter((t) => !t.includes('max>=0')),
    '',
  ].join('\n');
  return {
    stdout: text,
    [`${OUT}/k6_${RUN}.json`]: JSON.stringify(data, null, 2),
    [`${OUT}/k6_${RUN}.txt`]: text,
  };
}
