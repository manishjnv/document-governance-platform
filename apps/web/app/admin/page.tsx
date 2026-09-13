'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw, Search, ShieldCheck } from 'lucide-react';
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
import { PageHeader, KpiTile, Chip, SkeletonRows, AlertBanner } from '@/components/app';
import { cn } from '@/lib/utils';

interface Org {
  org_id: string;
  name: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  user_count: number;
  created_at: string;
  run_allowance: number;
}

interface Person {
  name: string;
  email: string;
  role: string;
  active: boolean;
  joined: string | null;
  last_sign_in: string | null;
  documents_uploaded: number;
  reviews_run: number;
  last_activity: string | null;
  workspace: string | null;
}

interface Overview {
  generated_at: string;
  totals: {
    members: number;
    active_members: number;
    sign_ins_last_7_days: number;
    sign_ins_last_30_days: number;
    documents: number;
    documents_last_7_days: number;
    reviews: number;
    reviews_last_7_days: number;
    findings: number;
  };
  people: Person[];
  recent_sign_ins: {
    who: string;
    when: string;
    how: string;
    device: string | null;
    from_ip: string | null;
  }[];
  recent_activity: { who: string; what: string; when: string }[];
  ai_usage: {
    reviews_completed: number;
    reviews_failed: number;
    checks_per_review: number;
    ai_calls_estimate: number;
    average_review_seconds: number | null;
    models_in_use: string[];
    last_review_at: string | null;
  };
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never';
  const then = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z').getTime();
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months > 1 ? 's' : ''} ago`;
}

function SearchBox({
  value,
  onChange,
  placeholder,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  className?: string;
}) {
  return (
    <div className={cn('relative', className)}>
      <Search
        size={14}
        strokeWidth={2}
        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="h-9 w-full rounded-lg border border-input bg-card pl-8 pr-2.5 text-[13px] text-foreground outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-[3px] focus:ring-accent"
      />
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [peopleQuery, setPeopleQuery] = useState('');
  const [signInQuery, setSignInQuery] = useState('');
  const [activityQuery, setActivityQuery] = useState('');
  const [orgs, setOrgs] = useState<Org[] | null>(null);
  const [orgError, setOrgError] = useState('');
  const [savingOrg, setSavingOrg] = useState<string | null>(null);
  const [runDrafts, setRunDrafts] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }
      const me = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!me.ok) {
        router.push('/login');
        return;
      }
      const meBody = await me.json();
      if (meBody.is_platform_admin !== true) {
        router.push('/dashboard');
        return;
      }
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('Could not load the admin overview.');
      setData(await resp.json());
      setError('');

      try {
        const orgsResp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/orgs`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!orgsResp.ok) throw new Error('Could not load organisations.');
        setOrgs(await orgsResp.json());
        setOrgError('');
      } catch (orgErr) {
        setOrgError(orgErr instanceof Error ? orgErr.message : 'Could not load organisations.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const updateOrgTier = async (orgId: string, tier: Org['subscription_tier']) => {
    const previous = orgs;
    const token = localStorage.getItem('access_token');
    setOrgs((cur) =>
      cur ? cur.map((o) => (o.org_id === orgId ? { ...o, subscription_tier: tier } : o)) : cur
    );
    setSavingOrg(orgId);
    setOrgError('');
    try {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/orgs/${orgId}/tier`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ subscription_tier: tier }),
      });
      const body = await resp.json().catch(() => null);
      if (!resp.ok) {
        setOrgs(previous);
        setOrgError(body?.detail || 'Could not update the tier.');
        return;
      }
      setOrgs((cur) => (cur ? cur.map((o) => (o.org_id === orgId ? { ...o, ...body } : o)) : cur));
    } catch {
      setOrgs(previous);
      setOrgError('Could not update the tier.');
    } finally {
      setSavingOrg(null);
    }
  };

  const updateRunAllowance = async (orgId: string, value: number) => {
    const previous = orgs;
    const token = localStorage.getItem('access_token');
    setSavingOrg(orgId);
    setOrgError('');
    try {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/orgs/${orgId}/run-allowance`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ run_allowance: value }),
      });
      const body = await resp.json().catch(() => null);
      if (!resp.ok) {
        setOrgs(previous);
        setOrgError(body?.detail || 'Could not update the run allowance.');
        return;
      }
      setOrgs((cur) => (cur ? cur.map((o) => (o.org_id === orgId ? { ...o, ...body } : o)) : cur));
    } catch {
      setOrgs(previous);
      setOrgError('Could not update the run allowance.');
    } finally {
      setSavingOrg(null);
    }
  };

  useEffect(() => {
    load();
    // Keep the numbers fresh without the admin having to click Refresh --
    // re-fetch every 60s while the tab is visible.
    const interval = setInterval(() => {
      if (!document.hidden) load();
    }, 60_000);
    const onVisible = () => {
      if (!document.hidden) load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <ShieldCheck size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            Admin
          </span>
        }
        actions={
          <>
            {data && (
              <span className="text-xs text-ink3">Last updated {timeAgo(data.generated_at)}</span>
            )}
            <Button size="sm" variant="outline" onClick={load} disabled={loading}>
              <RefreshCw size={14} strokeWidth={2} className={cn('mr-1.5', loading && 'animate-spin')} aria-hidden="true" />
              Refresh
            </Button>
          </>
        }
      />

      {error && (
        <AlertBanner kind="error" className="mb-3">
          {error}
        </AlertBanner>
      )}

      {!data && loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <>
          {/* Headline numbers */}
          <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <KpiTile
              value={data.totals.members}
              label="Members"
              sub={`${data.totals.active_members} active`}
            />
            <KpiTile
              value={data.totals.sign_ins_last_7_days}
              label="Sign-ins this week"
              sub={`${data.totals.sign_ins_last_30_days} in the last 30 days`}
            />
            <KpiTile
              value={data.totals.documents}
              label="Documents"
              sub={`${data.totals.documents_last_7_days} added this week`}
            />
            <KpiTile
              value={data.totals.reviews}
              label="AI reviews"
              sub={`${data.totals.reviews_last_7_days} this week`}
            />
            <KpiTile value={data.totals.findings} label="Issues found" sub="across all reviews" />
          </div>

          {/* Organisations */}
          <div className="mb-3 rounded-[10px] border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h2 className="text-sm font-semibold">Organisations</h2>
              <p className="mt-1 max-w-2xl text-[12.5px] text-muted-foreground">
                Free-tier organisations can upload and configure but cannot start reviews or MITRE
                assessments. Grant a number of runs, or set pro/enterprise for unlimited. Requests
                arrive by email with source assessment_request / review_request.
              </p>
              {orgError && (
                <p role="alert" className="mt-1.5 text-xs text-sev-crit">
                  {orgError}
                </p>
              )}
            </div>
            <div className="p-0">
              {!orgs ? (
                <div className="p-4">
                  <SkeletonRows rows={3} />
                </div>
              ) : orgs.length === 0 ? (
                <p className="p-4 text-xs text-muted-foreground">No organisations yet.</p>
              ) : (
                <Table className="cards">
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Organisation</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead>Runs</TableHead>
                      <TableHead className="text-right">Members</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orgs.map((org) => (
                      <TableRow key={org.org_id}>
                        <TableCell className="nolbl font-medium" data-th="Organisation">
                          {org.name}
                        </TableCell>
                        <TableCell data-th="Tier">
                          <Chip tone={org.subscription_tier === 'free' ? 'neutral' : 'pro'} xs className="uppercase tracking-wide">
                            {org.subscription_tier}
                          </Chip>
                        </TableCell>
                        <TableCell data-th="Runs">
                          {org.subscription_tier === 'free' ? (
                            <span className="flex items-center gap-1.5">
                              <input
                                type="number"
                                min={0}
                                max={1000}
                                aria-label="Runs to grant"
                                value={runDrafts[org.org_id] ?? String(org.run_allowance)}
                                disabled={savingOrg === org.org_id}
                                onChange={(e) =>
                                  setRunDrafts((prev) => ({ ...prev, [org.org_id]: e.target.value }))
                                }
                                className="h-[30px] w-20 rounded-lg border border-input bg-card px-2 text-xs tabular-nums text-right"
                              />
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={savingOrg === org.org_id}
                                onClick={() => {
                                  const raw = runDrafts[org.org_id] ?? String(org.run_allowance);
                                  const value = Math.max(0, Math.min(1000, Number(raw) || 0));
                                  updateRunAllowance(org.org_id, value);
                                }}
                              >
                                Set
                              </Button>
                            </span>
                          ) : (
                            <span className="text-muted-foreground">Unlimited</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right" data-th="Members">
                          <span className="font-semibold tabular-nums text-foreground">{org.user_count}</span>
                        </TableCell>
                        <TableCell className="text-muted-foreground" data-th="Created">
                          <span className="tabular-nums">
                            {new Date(org.created_at).toLocaleDateString('en-GB')}
                          </span>
                        </TableCell>
                        <TableCell className="text-right" data-th="Actions">
                          <select
                            value={org.subscription_tier}
                            aria-label={`Tier for ${org.name}`}
                            disabled={savingOrg === org.org_id}
                            onChange={(e) =>
                              updateOrgTier(org.org_id, e.target.value as Org['subscription_tier'])
                            }
                            className="h-[30px] rounded-lg border border-input bg-card px-2 text-xs"
                          >
                            <option value="free">free</option>
                            <option value="pro">pro</option>
                            <option value="enterprise">enterprise</option>
                          </select>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>

          {/* People */}
          <div className="mb-3 rounded-[10px] border border-border bg-card">
            <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
              <h2 className="text-sm font-semibold">People</h2>
              <SearchBox
                value={peopleQuery}
                onChange={setPeopleQuery}
                placeholder="Search people…"
                className="w-full max-w-[220px]"
              />
            </div>
            <div className="p-0">
              <Table className="cards">
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    {data.people.some((p) => p.workspace) && <TableHead>Workspace</TableHead>}
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead>Last sign-in</TableHead>
                    <TableHead className="text-right">Documents</TableHead>
                    <TableHead className="text-right">Reviews</TableHead>
                    <TableHead>Last active</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.people
                    .filter((p) =>
                      `${p.name} ${p.email} ${p.role} ${p.workspace ?? ''}`
                        .toLowerCase()
                        .includes(peopleQuery.toLowerCase())
                    )
                    .map((p) => (
                      <TableRow key={p.email}>
                        <TableCell className="nolbl font-medium" data-th="Name">
                          {p.name}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground" data-th="Email">
                          {p.email}
                        </TableCell>
                        <TableCell className="capitalize" data-th="Role">
                          {p.role}
                        </TableCell>
                        {data.people.some((x) => x.workspace) && (
                          <TableCell className="text-muted-foreground" data-th="Workspace">
                            {p.workspace ?? '—'}
                          </TableCell>
                        )}
                        <TableCell data-th="Status">
                          <Chip tone={p.active ? 'ok' : 'neutral'} xs className="uppercase tracking-wide">
                            {p.active ? 'Active' : 'Suspended'}
                          </Chip>
                        </TableCell>
                        <TableCell className="text-muted-foreground" data-th="Joined">
                          {timeAgo(p.joined)}
                        </TableCell>
                        <TableCell data-th="Last sign-in">{timeAgo(p.last_sign_in)}</TableCell>
                        <TableCell className="text-right" data-th="Documents">
                          <span className="font-semibold tabular-nums text-foreground">{p.documents_uploaded}</span>
                        </TableCell>
                        <TableCell className="text-right" data-th="Reviews">
                          <span className="font-semibold tabular-nums text-foreground">{p.reviews_run}</span>
                        </TableCell>
                        <TableCell data-th="Last active">{timeAgo(p.last_activity)}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="mb-3 grid gap-3 lg:grid-cols-2">
            {/* Recent sign-ins */}
            <div className="rounded-[10px] border border-border bg-card">
              <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold">Recent sign-ins</h2>
                <SearchBox
                  value={signInQuery}
                  onChange={setSignInQuery}
                  placeholder="Search sign-ins…"
                  className="w-full max-w-[190px]"
                />
              </div>
              <div className="p-0">
                {data.recent_sign_ins.length === 0 ? (
                  <p className="p-4 text-xs text-muted-foreground">No sign-ins recorded yet.</p>
                ) : (
                  <ul className="max-h-72 divide-y divide-border overflow-y-auto">
                    {data.recent_sign_ins
                      .filter((s) =>
                        `${s.who} ${s.how} ${s.device ?? ''} ${s.from_ip ?? ''}`
                          .toLowerCase()
                          .includes(signInQuery.toLowerCase())
                      )
                      .map((s, i) => (
                        <li key={i} className="flex justify-between gap-2 px-4 py-2 text-[13px]">
                          <span className="min-w-0 truncate">
                            <span className="font-medium">{s.who}</span>
                            <span className="text-muted-foreground"> · {s.how}</span>
                            {s.device && <span className="text-muted-foreground"> · {s.device}</span>}
                            {s.from_ip && <span className="text-muted-foreground"> · from {s.from_ip}</span>}
                          </span>
                          <span className="shrink-0 tabular-nums text-xs text-ink3">{timeAgo(s.when)}</span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Recent activity */}
            <div className="rounded-[10px] border border-border bg-card">
              <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold">Recent activity</h2>
                <SearchBox
                  value={activityQuery}
                  onChange={setActivityQuery}
                  placeholder="Search activity…"
                  className="w-full max-w-[190px]"
                />
              </div>
              <div className="p-0">
                {data.recent_activity.length === 0 ? (
                  <p className="p-4 text-xs text-muted-foreground">Nothing yet.</p>
                ) : (
                  <ul className="max-h-72 divide-y divide-border overflow-y-auto">
                    {data.recent_activity
                      .filter((a) => `${a.who} ${a.what}`.toLowerCase().includes(activityQuery.toLowerCase()))
                      .map((a, i) => (
                        <li key={i} className="flex justify-between gap-2 px-4 py-2 text-[13px]">
                          <span className="min-w-0 truncate">
                            <span className="font-medium">{a.who}</span>
                            <span className="text-muted-foreground"> — {a.what}</span>
                          </span>
                          <span className="shrink-0 tabular-nums text-xs text-ink3">{timeAgo(a.when)}</span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* AI usage */}
          <div className="rounded-[10px] border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h2 className="text-sm font-semibold">AI usage</h2>
            </div>
            <div className="p-4">
              <div className="mb-2 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <KpiTile value={data.ai_usage.reviews_completed} label="Reviews finished" />
                <KpiTile value={data.ai_usage.reviews_failed} label="Reviews failed" tone={data.ai_usage.reviews_failed > 0 ? 'crit' : 'default'} />
                <KpiTile value={data.ai_usage.checks_per_review} label="Checks per review" />
                <KpiTile
                  value={data.ai_usage.ai_calls_estimate}
                  label="AI calls (approx.)"
                  sub="finished reviews × checks"
                />
                <KpiTile
                  value={
                    data.ai_usage.average_review_seconds != null
                      ? `${Math.round(data.ai_usage.average_review_seconds)}s`
                      : '—'
                  }
                  label="Average review time"
                />
                <KpiTile value={timeAgo(data.ai_usage.last_review_at)} label="Last review" />
              </div>
              {data.ai_usage.models_in_use.length > 0 && (
                <p className="text-xs text-ink3">
                  AI models in use:{' '}
                  <span className="font-mono">{data.ai_usage.models_in_use.join(', ')}</span>
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
