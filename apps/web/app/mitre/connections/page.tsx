'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Pencil, Plug, Plus, Trash2 } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { AssessmentListItem, SiemConnection, fmtDate } from '../lib';
import { CoverageSparkline } from '../components/CoverageSparkline';
import {
  PageHeader,
  Chip,
  EmptyState,
  SkeletonRows,
  AlertBanner,
  ConfirmDialog,
} from '@/components/app';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']; // 0 = Monday, matches the API

const INPUT_CLS =
  'h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-accent';
const LABEL_CLS = 'mb-1 block text-xs font-medium text-muted-foreground';

const SENTINEL_FIELDS = [
  ['tenant_id', 'Tenant ID (GUID)'],
  ['client_id', 'Client ID (GUID)'],
  ['subscription_id', 'Subscription ID (GUID)'],
  ['resource_group', 'Resource group'],
  ['workspace', 'Log Analytics workspace'],
] as const;

const emptyForm = () => ({
  platform: 'sentinel' as 'sentinel' | 'splunk',
  name: '',
  sentinel: { tenant_id: '', client_id: '', subscription_id: '', resource_group: '', workspace: '' },
  splunk: { host: '', port: '8089', app: '' },
  secret: '',
  cadence: '' as '' | 'daily' | 'weekly',
  hour: '2',
  weekday: '0',
});

/** Phase 13d admin view, upgraded to full self-service: create/edit/delete
 * saved SIEM connections (Sentinel/Splunk), set the pull schedule, test,
 * pull now, and see each connection's coverage trend across its runs.
 * Server enforces admin-only regardless. */
export default function SiemConnectionsPage() {
  const router = useRouter();
  const [connections, setConnections] = useState<SiemConnection[] | null>(null);
  const [assessments, setAssessments] = useState<AssessmentListItem[] | null>(null);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState<string | null>(null);
  const [pulling, setPulling] = useState<string | null>(null);
  const [rowMsg, setRowMsg] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<SiemConnection | 'new' | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [pendingDelete, setPendingDelete] = useState<SiemConnection | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = () =>
    Promise.all([
      axios
        .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections`, {
          headers: authHeaders(),
        })
        .then((res) => setConnections(res.data))
        .catch((err) => {
          if (err.response?.status === 401) router.push('/login');
          else if (err.response?.status === 403)
            setError('SIEM connections are managed by org admins.');
          else setError(err.response?.data?.detail || 'Failed to load connections');
        }),
      // trend data — best-effort, the page works without it
      axios
        .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
          headers: authHeaders(),
        })
        .then((res) => setAssessments(res.data))
        .catch(() => {}),
    ]);

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openNew = () => {
    setForm(emptyForm());
    setFormError('');
    setEditing('new');
  };

  const openEdit = (c: SiemConnection) => {
    // stored splunk port is a number in JSONB — coerce everything to string
    setForm({
      platform: c.platform === 'splunk' ? 'splunk' : 'sentinel',
      name: c.name,
      sentinel: {
        tenant_id: String(c.config.tenant_id ?? ''),
        client_id: String(c.config.client_id ?? ''),
        subscription_id: String(c.config.subscription_id ?? ''),
        resource_group: String(c.config.resource_group ?? ''),
        workspace: String(c.config.workspace ?? ''),
      },
      splunk: {
        host: String(c.config.host ?? ''),
        port: String(c.config.port ?? '8089'),
        app: String(c.config.app ?? ''),
      },
      secret: '',
      cadence: c.schedule_cadence ?? '',
      hour: String(c.schedule_hour_utc ?? 2),
      weekday: String(c.schedule_weekday ?? 0),
    });
    setFormError('');
    setEditing(c);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const config =
      form.platform === 'sentinel'
        ? {
            tenant_id: form.sentinel.tenant_id.trim(),
            client_id: form.sentinel.client_id.trim(),
            subscription_id: form.sentinel.subscription_id.trim(),
            resource_group: form.sentinel.resource_group.trim(),
            workspace: form.sentinel.workspace.trim(),
          }
        : {
            host: form.splunk.host.trim(),
            port: Number(form.splunk.port) || 8089,
            ...(form.splunk.app.trim() ? { app: form.splunk.app.trim() } : {}),
          };
    // schedule rides as a trio — cadence null turns auto-runs off
    const schedule =
      form.cadence === ''
        ? { schedule_cadence: null, schedule_hour_utc: null, schedule_weekday: null }
        : {
            schedule_cadence: form.cadence,
            schedule_hour_utc: Number(form.hour),
            schedule_weekday: form.cadence === 'weekly' ? Number(form.weekday) : null,
          };
    if (editing === 'new' && !form.secret.trim()) {
      setFormError(
        form.platform === 'sentinel'
          ? 'The client secret is required — it is stored encrypted and never shown again.'
          : 'The auth token is required — it is stored encrypted and never shown again.'
      );
      return;
    }
    setSaving(true);
    setFormError('');
    try {
      if (editing === 'new') {
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections`,
          {
            platform: form.platform,
            config,
            secret: form.secret,
            ...(form.name.trim() ? { name: form.name.trim() } : {}),
            ...schedule,
          },
          { headers: authHeaders() }
        );
      } else if (editing) {
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections/${editing.connection_id}`,
          {
            name: form.name.trim(), // empty = keep current (server no-op)
            config,
            ...(form.secret.trim() ? { secret: form.secret } : {}),
            ...schedule,
          },
          { headers: authHeaders() }
        );
      }
      setEditing(null);
      setForm(emptyForm());
      await load();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Could not save the connection');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (c: SiemConnection) => {
    setPendingDelete(c);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      setDeleteBusy(true);
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections/${pendingDelete.connection_id}`,
        { headers: authHeaders() }
      );
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not delete the connection');
    } finally {
      setDeleteBusy(false);
      setPendingDelete(null);
    }
  };

  const handleTest = async (connectionId: string) => {
    setTesting(connectionId);
    setRowMsg((prev) => ({ ...prev, [connectionId]: '' }));
    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections/${connectionId}/test`,
        null,
        { headers: authHeaders() }
      );
      setRowMsg((prev) => ({
        ...prev,
        [connectionId]: `OK — ${res.data.rule_count} rules reachable`,
      }));
    } catch (err: any) {
      setRowMsg((prev) => ({
        ...prev,
        [connectionId]: err.response?.data?.detail || 'Test failed',
      }));
    } finally {
      setTesting(null);
    }
  };

  const handlePullNow = async (connectionId: string) => {
    setPulling(connectionId);
    setRowMsg((prev) => ({ ...prev, [connectionId]: '' }));
    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/from-connection/${connectionId}`,
        {},
        { headers: authHeaders() }
      );
      const id = res.data.assessment_id;
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${id}/run`,
        null,
        { headers: authHeaders() }
      );
      router.push(`/mitre/${id}`);
    } catch (err: any) {
      setRowMsg((prev) => ({
        ...prev,
        [connectionId]: err.response?.data?.detail || 'Pull failed',
      }));
      setPulling(null);
    }
  };

  const scheduleLabel = (c: SiemConnection) => {
    if (!c.schedule_cadence) return 'Off';
    const hour = `${String(c.schedule_hour_utc).padStart(2, '0')}:00 UTC`;
    return c.schedule_cadence === 'daily'
      ? `Daily · ${hour}`
      : `Weekly · ${WEEKDAYS[c.schedule_weekday ?? 0]} ${hour}`;
  };

  /** Coverage trend for one connection: latest %, delta vs the previous
   * completed run, and the sparkline across all of its runs. */
  const trendFor = (c: SiemConnection) => {
    const runs = (assessments ?? []).filter(
      (a) => a.siem?.connection_id === c.connection_id
    );
    const completed = runs.filter(
      (r) => r.status === 'completed' && r.strict_pct !== null && !r.archived
    );
    if (completed.length === 0) return <span className="text-[12.5px] text-muted-foreground">—</span>;
    const latest = completed[0]; // list is newest-first
    const previous = completed[1];
    const delta =
      previous !== undefined
        ? Math.round(((latest.strict_pct as number) - (previous.strict_pct as number)) * 10) / 10
        : null;
    return (
      <div className="space-y-0.5">
        <Link
          href={`/mitre/${latest.assessment_id}`}
          className="text-sm font-medium hover:underline"
        >
          {latest.strict_pct}%
          {delta !== null && (
            <span
              className={cn(
                'ml-1.5 text-xs font-medium',
                delta > 0 ? 'text-ok' : delta < 0 ? 'text-sev-crit' : 'text-muted-foreground'
              )}
            >
              {delta > 0 ? `+${delta}` : delta}
            </span>
          )}
        </Link>
        <CoverageSparkline items={runs} />
      </div>
    );
  };

  return (
    <AppShell>
      <TooltipProvider delayDuration={200}>
        <PageHeader
          title={
            <span className="flex items-center gap-2">
              <Plug size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
              SIEM connections
            </span>
          }
          back={{ href: '/mitre', label: 'Assessments' }}
          actions={
            <Button size="sm" onClick={openNew}>
              <Plus size={14} aria-hidden="true" /> Add connection
            </Button>
          }
        />

        {error && (
          <AlertBanner kind="error" className="mb-4">
            {error}
          </AlertBanner>
        )}

        {editing !== null && (
          <form onSubmit={handleSave} className="mb-4 rounded-[10px] border border-border bg-card p-4">
            <h2 className="mb-1 text-sm font-semibold">
              {editing === 'new' ? 'Add connection' : `Edit ${editing.name}`}
            </h2>
            <p className="mb-3 max-w-xl text-[12.5px] text-muted-foreground">
              Read-only pull of your detection rules. The{' '}
              {form.platform === 'sentinel' ? 'client secret' : 'auth token'} is stored
              encrypted and never shown again.
              {form.platform === 'sentinel' &&
                ' The service principal needs the Microsoft Sentinel Reader role.'}
            </p>

            {editing === 'new' && (
              <div
                className="mb-3 flex max-w-md gap-1 rounded-lg border border-border p-1"
                role="tablist"
                aria-label="Platform"
              >
                {(
                  [
                    ['sentinel', 'Microsoft Sentinel'],
                    ['splunk', 'Splunk'],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={form.platform === key}
                    onClick={() => setForm((prev) => ({ ...prev, platform: key }))}
                    className={cn(
                      'flex-1 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors duration-150 ease-app',
                      form.platform === key
                        ? 'bg-accent-soft text-primary'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label htmlFor="conn-name" className={LABEL_CLS}>
                  Name <span className="font-normal text-muted-foreground">(optional)</span>
                </label>
                <input
                  id="conn-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  autoComplete="off"
                  className={INPUT_CLS}
                />
              </div>

              {form.platform === 'sentinel' &&
                SENTINEL_FIELDS.map(([field, label]) => (
                  <div key={field}>
                    <label htmlFor={`conn-${field}`} className={LABEL_CLS}>
                      {label}
                    </label>
                    <input
                      id={`conn-${field}`}
                      type="text"
                      value={form.sentinel[field]}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          sentinel: { ...prev.sentinel, [field]: e.target.value },
                        }))
                      }
                      autoComplete="off"
                      className={INPUT_CLS}
                    />
                  </div>
                ))}

              {form.platform === 'splunk' && (
                <>
                  <div>
                    <label htmlFor="conn-host" className={LABEL_CLS}>
                      Host <span className="font-normal text-muted-foreground">(e.g. acme.splunkcloud.com)</span>
                    </label>
                    <input
                      id="conn-host"
                      type="text"
                      value={form.splunk.host}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, splunk: { ...prev.splunk, host: e.target.value } }))
                      }
                      autoComplete="off"
                      className={INPUT_CLS}
                    />
                  </div>
                  <div>
                    <label htmlFor="conn-port" className={LABEL_CLS}>
                      Management port
                    </label>
                    <input
                      id="conn-port"
                      type="text"
                      inputMode="numeric"
                      value={form.splunk.port}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, splunk: { ...prev.splunk, port: e.target.value } }))
                      }
                      autoComplete="off"
                      className={INPUT_CLS}
                    />
                  </div>
                  <div>
                    <label htmlFor="conn-app" className={LABEL_CLS}>
                      App <span className="font-normal text-muted-foreground">(optional — all apps if empty)</span>
                    </label>
                    <input
                      id="conn-app"
                      type="text"
                      value={form.splunk.app}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, splunk: { ...prev.splunk, app: e.target.value } }))
                      }
                      autoComplete="off"
                      className={INPUT_CLS}
                    />
                  </div>
                </>
              )}

              <div>
                <label htmlFor="conn-secret" className={LABEL_CLS}>
                  {form.platform === 'sentinel' ? 'Client secret' : 'Auth token'}{' '}
                  <span className="font-normal text-muted-foreground">
                    {editing === 'new' ? '(stored encrypted)' : '(blank = keep saved)'}
                  </span>
                </label>
                <input
                  id="conn-secret"
                  type="password"
                  value={form.secret}
                  onChange={(e) => setForm((prev) => ({ ...prev, secret: e.target.value }))}
                  autoComplete="off"
                  className={INPUT_CLS}
                />
              </div>

              <div>
                <label htmlFor="conn-cadence" className={LABEL_CLS}>
                  Auto-pull schedule
                </label>
                <select
                  id="conn-cadence"
                  value={form.cadence}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, cadence: e.target.value as '' | 'daily' | 'weekly' }))
                  }
                  className={INPUT_CLS}
                >
                  <option value="">Off — manual pulls only</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>

              {form.cadence !== '' && (
                <div>
                  <label htmlFor="conn-hour" className={LABEL_CLS}>
                    Hour (UTC)
                  </label>
                  <select
                    id="conn-hour"
                    value={form.hour}
                    onChange={(e) => setForm((prev) => ({ ...prev, hour: e.target.value }))}
                    className={INPUT_CLS}
                  >
                    {Array.from({ length: 24 }, (_, h) => (
                      <option key={h} value={String(h)}>
                        {String(h).padStart(2, '0')}:00 UTC
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {form.cadence === 'weekly' && (
                <div>
                  <label htmlFor="conn-weekday" className={LABEL_CLS}>
                    Day of week
                  </label>
                  <select
                    id="conn-weekday"
                    value={form.weekday}
                    onChange={(e) => setForm((prev) => ({ ...prev, weekday: e.target.value }))}
                    className={INPUT_CLS}
                  >
                    {WEEKDAYS.map((day, i) => (
                      <option key={day} value={String(i)}>
                        {day}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {formError && (
              <p role="alert" className="mt-3 text-[13px] text-sev-crit">
                {formError}
              </p>
            )}

            <div className="mt-4 flex gap-2">
              <Button type="submit" size="sm" disabled={saving}>
                {saving ? 'Saving…' : editing === 'new' ? 'Save connection' : 'Save changes'}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setEditing(null)}
                disabled={saving}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}

        {connections === null && editing === null && !error && <SkeletonRows rows={2} />}

        {connections !== null && connections.length === 0 && !error && editing === null && (
          <EmptyState title="No saved connections yet. Add one to pull detection rules straight from Microsoft Sentinel or Splunk — on a schedule if you like. Saved secrets are encrypted at rest and never shown again." />
        )}

        {connections !== null && connections.length > 0 && (
          <div className="overflow-hidden rounded-[10px] border border-border bg-card">
            <Table className="tbl cards">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Connection</TableHead>
                  <TableHead>Schedule</TableHead>
                  <TableHead>Last pull</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead>Coverage trend</TableHead>
                  <TableHead className="min-w-[200px]">Last error</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {connections.map((c) => (
                  <TableRow key={c.connection_id}>
                    <TableCell className="nolbl" data-th="Connection">
                      <div className="text-[13px] font-medium">{c.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {c.platform === 'splunk'
                          ? `Splunk · ${c.config.host ?? ''}`
                          : `Sentinel · ${c.config.workspace ?? ''}`}
                      </div>
                    </TableCell>
                    <TableCell className="text-[12.5px]" data-th="Schedule">
                      {scheduleLabel(c)}
                    </TableCell>
                    <TableCell className="text-[12.5px] text-muted-foreground" data-th="Last pull">
                      {c.health.last_pull_at ? (
                        <>
                          {fmtDate(c.health.last_pull_at)}
                          <span className="block">{c.health.last_status}</span>
                        </>
                      ) : (
                        'never'
                      )}
                    </TableCell>
                    <TableCell data-th="Health">
                      <Chip tone={c.health.scheduled_failure_streak === 0 ? 'ok' : 'crit'} dot xs>
                        {c.health.scheduled_failure_streak === 0
                          ? 'Healthy'
                          : `${c.health.scheduled_failure_streak} failed in a row`}
                      </Chip>
                    </TableCell>
                    <TableCell data-th="Coverage trend">{trendFor(c)}</TableCell>
                    <TableCell className="text-[12.5px] text-muted-foreground" data-th="Last error">
                      {c.health.last_error ?? '—'}
                      {rowMsg[c.connection_id] && (
                        <span className="block font-medium text-foreground">
                          {rowMsg[c.connection_id]}
                        </span>
                      )}
                    </TableCell>
                    <TableCell data-th="Actions">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={testing === c.connection_id || pulling === c.connection_id}
                          onClick={() => handleTest(c.connection_id)}
                        >
                          {testing === c.connection_id ? 'Testing…' : 'Test'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pulling === c.connection_id || testing === c.connection_id}
                          onClick={() => handlePullNow(c.connection_id)}
                        >
                          {pulling === c.connection_id ? 'Pulling…' : 'Pull now'}
                        </Button>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={`Edit ${c.name}`}
                              onClick={() => openEdit(c)}
                              className="rounded-md p-1.5 text-muted-foreground transition-colors duration-150 ease-app hover:bg-muted hover:text-foreground"
                            >
                              <Pencil size={14} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>Edit</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={`Delete ${c.name}`}
                              onClick={() => handleDelete(c)}
                              className="rounded-md p-1.5 text-muted-foreground transition-colors duration-150 ease-app hover:bg-muted hover:text-sev-crit"
                            >
                              <Trash2 size={14} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>Delete</TooltipContent>
                        </Tooltip>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <ConfirmDialog
          open={pendingDelete !== null}
          onOpenChange={(open) => {
            if (!open) setPendingDelete(null);
          }}
          title="Delete connection"
          description={
            pendingDelete
              ? `Delete "${pendingDelete.name}"? Scheduled pulls stop; past assessments are kept.`
              : ''
          }
          confirmLabel="Delete"
          busy={deleteBusy}
          onConfirm={confirmDelete}
        />
      </TooltipProvider>
    </AppShell>
  );
}
