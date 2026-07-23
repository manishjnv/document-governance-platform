'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

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
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative">
      <Search
        size={13}
        strokeWidth={2}
        className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="h-7 w-44 rounded-md border border-input bg-background pl-7 pr-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
      />
    </div>
  );
}

function StatTile({ value, label, sub }: { value: number | string; label: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="py-3 text-center">
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs font-medium text-foreground">{label}</div>
        {sub && <div className="text-[11px] text-muted-foreground">{sub}</div>}
      </CardContent>
    </Card>
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
      if (meBody.role !== 'admin') {
        router.push('/dashboard');
        return;
      }
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('Could not load the admin overview.');
      setData(await resp.json());
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
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
      <div className="flex items-center justify-between mb-3">
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
          Admin
        </h1>
        <div className="flex items-center gap-2">
          {data && (
            <span className="text-[11px] text-muted-foreground">
              Last updated {timeAgo(data.generated_at)}
            </span>
          )}
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            <RefreshCw size={14} strokeWidth={2} className={cn('mr-1.5', loading && 'animate-spin')} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="bg-destructive/10 border border-destructive/30 rounded-md p-3 mb-3 text-sm">
          {error}
        </div>
      )}

      {!data && loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <>
          {/* Headline numbers */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-1.5 mb-3">
            <StatTile
              value={data.totals.members}
              label="Members"
              sub={`${data.totals.active_members} active`}
            />
            <StatTile
              value={data.totals.sign_ins_last_7_days}
              label="Sign-ins this week"
              sub={`${data.totals.sign_ins_last_30_days} in the last 30 days`}
            />
            <StatTile
              value={data.totals.documents}
              label="Documents"
              sub={`${data.totals.documents_last_7_days} added this week`}
            />
            <StatTile
              value={data.totals.reviews}
              label="AI reviews"
              sub={`${data.totals.reviews_last_7_days} this week`}
            />
            <StatTile value={data.totals.findings} label="Issues found" sub="across all reviews" />
          </div>

          {/* People */}
          <Card className="mb-3">
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-1 pt-3">
              <CardTitle className="text-sm">People</CardTitle>
              <SearchBox value={peopleQuery} onChange={setPeopleQuery} placeholder="Search people…" />
            </CardHeader>
            <CardContent className="pb-3 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-muted-foreground border-b">
                    <th className="py-1.5 pr-3 font-medium">Name</th>
                    <th className="py-1.5 pr-3 font-medium">Email</th>
                    <th className="py-1.5 pr-3 font-medium">Role</th>
                    <th className="py-1.5 pr-3 font-medium">Status</th>
                    <th className="py-1.5 pr-3 font-medium">Joined</th>
                    <th className="py-1.5 pr-3 font-medium">Last sign-in</th>
                    <th className="py-1.5 pr-3 font-medium text-right">Documents</th>
                    <th className="py-1.5 pr-3 font-medium text-right">Reviews</th>
                    <th className="py-1.5 font-medium">Last active</th>
                  </tr>
                </thead>
                <tbody>
                  {data.people.filter((p) =>
                    `${p.name} ${p.email} ${p.role}`.toLowerCase().includes(peopleQuery.toLowerCase())
                  ).map((p) => (
                    <tr key={p.email} className="border-b last:border-0">
                      <td className="py-1.5 pr-3 font-medium">{p.name}</td>
                      <td className="py-1.5 pr-3 text-muted-foreground">{p.email}</td>
                      <td className="py-1.5 pr-3 capitalize">{p.role}</td>
                      <td className="py-1.5 pr-3">
                        <span
                          className={cn(
                            'px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide',
                            p.active ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700'
                          )}
                        >
                          {p.active ? 'Active' : 'Suspended'}
                        </span>
                      </td>
                      <td className="py-1.5 pr-3 text-muted-foreground">{timeAgo(p.joined)}</td>
                      <td className="py-1.5 pr-3">{timeAgo(p.last_sign_in)}</td>
                      <td className="py-1.5 pr-3 text-right">{p.documents_uploaded}</td>
                      <td className="py-1.5 pr-3 text-right">{p.reviews_run}</td>
                      <td className="py-1.5">{timeAgo(p.last_activity)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <div className="grid lg:grid-cols-2 gap-3 mb-3">
            {/* Recent sign-ins */}
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0 pb-1 pt-3">
                <CardTitle className="text-sm">Recent sign-ins</CardTitle>
                <SearchBox value={signInQuery} onChange={setSignInQuery} placeholder="Search sign-ins…" />
              </CardHeader>
              <CardContent className="pb-3">
                {data.recent_sign_ins.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No sign-ins recorded yet.</p>
                ) : (
                  <ul className="space-y-1.5 text-xs max-h-72 overflow-y-auto">
                    {data.recent_sign_ins.filter((s) =>
                      `${s.who} ${s.how} ${s.device ?? ''} ${s.from_ip ?? ''}`
                        .toLowerCase()
                        .includes(signInQuery.toLowerCase())
                    ).map((s, i) => (
                      <li key={i} className="flex justify-between gap-2">
                        <span className="min-w-0 truncate">
                          <span className="font-medium">{s.who}</span>
                          <span className="text-muted-foreground"> · {s.how}</span>
                          {s.device && <span className="text-muted-foreground"> · {s.device}</span>}
                          {s.from_ip && <span className="text-muted-foreground"> · from {s.from_ip}</span>}
                        </span>
                        <span className="shrink-0 text-muted-foreground">{timeAgo(s.when)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            {/* Recent activity */}
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0 pb-1 pt-3">
                <CardTitle className="text-sm">Recent activity</CardTitle>
                <SearchBox value={activityQuery} onChange={setActivityQuery} placeholder="Search activity…" />
              </CardHeader>
              <CardContent className="pb-3">
                {data.recent_activity.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Nothing yet.</p>
                ) : (
                  <ul className="space-y-1.5 text-xs max-h-72 overflow-y-auto">
                    {data.recent_activity.filter((a) =>
                      `${a.who} ${a.what}`.toLowerCase().includes(activityQuery.toLowerCase())
                    ).map((a, i) => (
                      <li key={i} className="flex justify-between gap-2">
                        <span className="min-w-0 truncate">
                          <span className="font-medium">{a.who}</span>
                          <span className="text-muted-foreground"> — {a.what}</span>
                        </span>
                        <span className="shrink-0 text-muted-foreground">{timeAgo(a.when)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          {/* AI usage */}
          <Card>
            <CardHeader className="pb-1 pt-3">
              <CardTitle className="text-sm">AI usage</CardTitle>
            </CardHeader>
            <CardContent className="pb-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5 mb-2">
                <StatTile value={data.ai_usage.reviews_completed} label="Reviews finished" />
                <StatTile value={data.ai_usage.reviews_failed} label="Reviews failed" />
                <StatTile value={data.ai_usage.checks_per_review} label="Checks per review" />
                <StatTile
                  value={data.ai_usage.ai_calls_estimate}
                  label="AI calls (approx.)"
                  sub="finished reviews × checks"
                />
                <StatTile
                  value={
                    data.ai_usage.average_review_seconds != null
                      ? `${Math.round(data.ai_usage.average_review_seconds)}s`
                      : '—'
                  }
                  label="Average review time"
                />
                <StatTile value={timeAgo(data.ai_usage.last_review_at)} label="Last review" />
              </div>
              {data.ai_usage.models_in_use.length > 0 && (
                <p className="text-[11px] text-muted-foreground">
                  AI models in use: {data.ai_usage.models_in_use.join(', ')}
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </AppShell>
  );
}
