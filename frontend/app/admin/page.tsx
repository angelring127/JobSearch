import { requireAdmin } from '@/lib/server/admin-auth';
import {
  getAdminDashboardData,
  AdminSourceRow,
  AuditLogRow,
  CrawlFailureRow,
  CrawlRunRow,
  DuplicateCandidateRow,
  MergeHistoryRow,
} from '@/lib/server/admin-data';
import {
  approveDuplicateAction,
  logoutAction,
  rejectDuplicateAction,
  rollbackMergeAction,
  runSourceAction,
  toggleSourceAction,
} from './actions';

export const dynamic = 'force-dynamic';

function formatDate(value: Date | null) {
  if (!value) {
    return '-';
  }
  return new Intl.DateTimeFormat('ko-CA', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Vancouver',
  }).format(value);
}

function statusClass(status: string | null) {
  if (status === 'ok') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (status === 'partial') {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  if (status === 'failed') {
    return 'border-red-200 bg-red-50 text-red-700';
  }
  if (status === 'running') {
    return 'border-blue-200 bg-blue-50 text-blue-700';
  }
  if (status === 'skipped') {
    return 'border-slate-200 bg-slate-50 text-slate-600';
  }
  return 'border-slate-200 bg-slate-50 text-slate-600';
}

function StatusBadge({ status }: { status: string | null }) {
  return (
    <span className={`inline-flex min-w-16 justify-center rounded-full border px-2 py-1 text-xs font-medium ${statusClass(status)}`}>
      {status || 'none'}
    </span>
  );
}

function SourceRow({ source }: { source: AdminSourceRow }) {
  const hasFailure = source.last_status === 'failed' || Boolean(source.last_error);

  return (
    <tr className={hasFailure ? 'bg-red-50/70' : 'bg-white'}>
      <td className="px-4 py-3">
        <div className="font-medium text-slate-950">{source.display_name}</div>
        <div className="text-xs text-slate-500">{source.source_key}</div>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-medium ${source.enabled ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
          {source.enabled ? 'active' : 'disabled'}
        </span>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={source.last_status} />
      </td>
      <td className="px-4 py-3 text-sm text-slate-700">{formatDate(source.last_run_at)}</td>
      <td className="px-4 py-3 text-sm text-slate-700">
        <span>{source.last_processed ?? 0}</span>
        <span className="mx-1 text-slate-300">/</span>
        <span className={source.last_failed ? 'font-medium text-red-700' : ''}>{source.last_failed ?? 0}</span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-700">{source.last_error || '-'}</td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          <form action={toggleSourceAction}>
            <input type="hidden" name="source_key" value={source.source_key} />
            <input type="hidden" name="enabled" value={source.enabled ? 'false' : 'true'} />
            <button className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100" type="submit">
              {source.enabled ? '끄기' : '켜기'}
            </button>
          </form>
          <form action={runSourceAction}>
            <input type="hidden" name="source_key" value={source.source_key} />
            <button
              className="rounded-md bg-slate-950 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              type="submit"
              disabled={!source.enabled}
            >
              실행
            </button>
          </form>
        </div>
      </td>
    </tr>
  );
}

function RunRow({ run }: { run: CrawlRunRow }) {
  return (
    <tr className="border-t border-slate-200">
      <td className="px-4 py-3 text-sm text-slate-600">#{run.id}</td>
      <td className="px-4 py-3">
        <div className="font-medium text-slate-900">{run.display_name}</div>
        <div className="text-xs text-slate-500">{run.trigger_type}</div>
      </td>
      <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
      <td className="px-4 py-3 text-sm text-slate-700">{formatDate(run.started_at)}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{run.duration_ms ?? '-'}ms</td>
      <td className="px-4 py-3 text-sm text-slate-700">{run.processed}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{run.created}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{run.updated}</td>
      <td className={run.failed ? 'px-4 py-3 text-sm font-medium text-red-700' : 'px-4 py-3 text-sm text-slate-700'}>{run.failed}</td>
    </tr>
  );
}

function FailureRow({ failure }: { failure: CrawlFailureRow }) {
  return (
    <tr className="border-t border-red-100 bg-red-50/60">
      <td className="px-4 py-3 text-sm text-slate-600">#{failure.run_id}</td>
      <td className="px-4 py-3 text-sm font-medium text-slate-900">{failure.display_name}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{failure.city || '-'}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{failure.msgid || '-'}</td>
      <td className="px-4 py-3 text-sm text-red-800">{failure.error_message}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{formatDate(failure.created_at)}</td>
    </tr>
  );
}

function wageRange(min: number | null, max: number | null) {
  if (!min && !max) {
    return '-';
  }
  if (min && max && min !== max) {
    return `$${min}-${max}`;
  }
  return `$${min || max}`;
}

function DuplicateCandidateCard({ candidate }: { candidate: DuplicateCandidateRow }) {
  return (
    <div className="rounded-md border border-amber-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-950">Candidate #{candidate.id}</div>
          <div className="text-xs text-slate-500">score {candidate.score}</div>
        </div>
        <div className="flex items-center gap-2">
          <form action={approveDuplicateAction}>
            <input type="hidden" name="candidate_id" value={candidate.id} />
            <button className="rounded-md bg-slate-950 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800" type="submit">
              승인
            </button>
          </form>
          <form action={rejectDuplicateAction}>
            <input type="hidden" name="candidate_id" value={candidate.id} />
            <button className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100" type="submit">
              거절
            </button>
          </form>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md bg-amber-50 p-3">
          <div className="text-xs font-medium uppercase text-amber-700">New source</div>
          <div className="mt-1 font-medium text-slate-950">{candidate.source_title || '-'}</div>
          <div className="mt-1 text-slate-600">{candidate.source_region || '-'} · {wageRange(candidate.source_wage_min, candidate.source_wage_max)}</div>
        </div>
        <div className="rounded-md bg-slate-50 p-3">
          <div className="text-xs font-medium uppercase text-slate-500">Existing job</div>
          <div className="mt-1 font-medium text-slate-950">{candidate.candidate_title || '-'}</div>
          <div className="mt-1 text-slate-600">{candidate.candidate_region || '-'} · {wageRange(candidate.candidate_wage_min, candidate.candidate_wage_max)}</div>
        </div>
      </div>
    </div>
  );
}

function MergeHistoryRowView({ item }: { item: MergeHistoryRow }) {
  const canRollback = item.action === 'auto_merge' || item.action === 'manual_merge';

  return (
    <tr className="border-t border-slate-200">
      <td className="px-4 py-3 text-sm text-slate-600">#{item.id}</td>
      <td className="px-4 py-3"><StatusBadge status={item.action} /></td>
      <td className="px-4 py-3 text-sm text-slate-900">{item.source_title || '-'}</td>
      <td className="px-4 py-3 text-sm text-slate-700">job #{item.job_id}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{formatDate(item.created_at)}</td>
      <td className="px-4 py-3 text-right">
        {canRollback ? (
          <form action={rollbackMergeAction}>
            <input type="hidden" name="history_id" value={item.id} />
            <button className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100" type="submit">
              롤백
            </button>
          </form>
        ) : (
          <span className="text-sm text-slate-400">-</span>
        )}
      </td>
    </tr>
  );
}

function AuditRow({ item }: { item: AuditLogRow }) {
  return (
    <tr className="border-t border-slate-200">
      <td className="px-4 py-3 text-sm text-slate-600">#{item.id}</td>
      <td className="px-4 py-3 text-sm font-medium text-slate-900">{item.action}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{item.target_type}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{item.target_id}</td>
      <td className="px-4 py-3 text-sm text-slate-700">{formatDate(item.created_at)}</td>
    </tr>
  );
}

export default async function AdminPage() {
  await requireAdmin();
  const { sources, recentRuns, recentFailures, duplicateCandidates, mergeHistory, auditLog } = await getAdminDashboardData();

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold">JobMap Admin</h1>
            <p className="text-sm text-slate-600">소스 상태, 최근 크롤링 실행, 수동 실행</p>
          </div>
          <form action={logoutAction}>
            <button className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100" type="submit">
              로그아웃
            </button>
          </form>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-6">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Sources</h2>
            <span className="text-sm text-slate-500">{sources.length} source</span>
          </div>
          <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
            <table className="w-full table-fixed">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="w-44 px-4 py-3">Source</th>
                  <th className="w-28 px-4 py-3">Enabled</th>
                  <th className="w-28 px-4 py-3">Status</th>
                  <th className="w-40 px-4 py-3">Last Run</th>
                  <th className="w-28 px-4 py-3">Done/Fail</th>
                  <th className="px-4 py-3">Failure</th>
                  <th className="w-44 px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {sources.map((source) => <SourceRow key={source.source_key} source={source} />)}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Recent Runs</h2>
            <span className="text-sm text-slate-500">{recentRuns.length} runs</span>
          </div>
          <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
            <table className="w-full table-fixed">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="w-20 px-4 py-3">Run</th>
                  <th className="w-44 px-4 py-3">Source</th>
                  <th className="w-28 px-4 py-3">Status</th>
                  <th className="w-44 px-4 py-3">Started</th>
                  <th className="w-28 px-4 py-3">Duration</th>
                  <th className="w-24 px-4 py-3">Processed</th>
                  <th className="w-24 px-4 py-3">Created</th>
                  <th className="w-24 px-4 py-3">Updated</th>
                  <th className="w-24 px-4 py-3">Failed</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.length ? recentRuns.map((run) => <RunRow key={run.id} run={run} />) : (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-500">아직 실행 이력이 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Failures</h2>
            <span className="text-sm text-slate-500">{recentFailures.length} items</span>
          </div>
          <div className="overflow-hidden rounded-md border border-red-100 bg-white">
            <table className="w-full table-fixed">
              <thead className="bg-red-50 text-left text-xs font-medium uppercase text-red-700">
                <tr>
                  <th className="w-20 px-4 py-3">Run</th>
                  <th className="w-36 px-4 py-3">Source</th>
                  <th className="w-32 px-4 py-3">City</th>
                  <th className="w-28 px-4 py-3">MsgID</th>
                  <th className="px-4 py-3">Message</th>
                  <th className="w-44 px-4 py-3">Time</th>
                </tr>
              </thead>
              <tbody>
                {recentFailures.length ? recentFailures.map((failure) => <FailureRow key={failure.id} failure={failure} />) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">최근 실패 항목이 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Duplicate Candidates</h2>
            <span className="text-sm text-slate-500">{duplicateCandidates.length} pending</span>
          </div>
          <div className="grid gap-3">
            {duplicateCandidates.length ? duplicateCandidates.map((candidate) => (
              <DuplicateCandidateCard key={candidate.id} candidate={candidate} />
            )) : (
              <div className="rounded-md border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
                검토할 중복 후보가 없습니다.
              </div>
            )}
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Merge History</h2>
            <span className="text-sm text-slate-500">{mergeHistory.length} records</span>
          </div>
          <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
            <table className="w-full table-fixed">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="w-20 px-4 py-3">ID</th>
                  <th className="w-36 px-4 py-3">Action</th>
                  <th className="px-4 py-3">Source Title</th>
                  <th className="w-28 px-4 py-3">Job</th>
                  <th className="w-44 px-4 py-3">Time</th>
                  <th className="w-28 px-4 py-3 text-right">Rollback</th>
                </tr>
              </thead>
              <tbody>
                {mergeHistory.length ? mergeHistory.map((item) => <MergeHistoryRowView key={item.id} item={item} />) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">merge 이력이 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Audit Log</h2>
            <span className="text-sm text-slate-500">{auditLog.length} events</span>
          </div>
          <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
            <table className="w-full table-fixed">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="w-20 px-4 py-3">ID</th>
                  <th className="w-44 px-4 py-3">Action</th>
                  <th className="w-40 px-4 py-3">Target</th>
                  <th className="px-4 py-3">Target ID</th>
                  <th className="w-44 px-4 py-3">Time</th>
                </tr>
              </thead>
              <tbody>
                {auditLog.length ? auditLog.map((item) => <AuditRow key={item.id} item={item} />) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">감사 로그가 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
