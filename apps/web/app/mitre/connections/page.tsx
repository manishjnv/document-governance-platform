'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Plug } from 'lucide-react';
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
import { cn } from '@/lib/utils';
import { SiemConnection, fmtDate } from '../lib';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/** Phase 13d admin view: saved SIEM connections with pull health. Creation/
 * editing stays API-driven for now — this surfaces state and lets an admin
 * verify a connection still works. Server enforces admin-only regardless. */
export default function SiemConnectionsPage() {
  const router = useRouter();
  const [connections, setConnections] = useState<SiemConnection[] | null>(null);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, string>>({});

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = () =>
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
      });

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTest = async (connectionId: string) => {
    setTesting(connectionId);
    setTestResult((prev) => ({ ...prev, [connectionId]: '' }));
    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/connections/${connectionId}/test`,
        null,
        { headers: authHeaders() }
      );
      setTestResult((prev) => ({
        ...prev,
        [connectionId]: `OK — ${res.data.rule_count} rules reachable`,
      }));
    } catch (err: any) {
      setTestResult((prev) => ({
        ...prev,
        [connectionId]: err.response?.data?.detail || 'Test failed',
      }));
    } finally {
      setTesting(null);
    }
  };

  const scheduleLabel = (c: SiemConnection) => {
    if (!c.schedule_cadence) return 'Off';
    const hour = `${String(c.schedule_hour_utc).padStart(2, '0')}:00 UTC`;
    return c.schedule_cadence === 'daily'
      ? `Daily · ${hour}`
      : `Weekly · ${WEEKDAYS[c.schedule_weekday ?? 0]} ${hour}`;
  };

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between gap-2">
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <Plug size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
          SIEM connections
        </h1>
        <Button asChild size="sm" variant="outline">
          <Link href="/mitre">
            <ArrowLeft size={14} className="mr-1" aria-hidden="true" /> Assessments
          </Link>
        </Button>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {connections !== null && connections.length === 0 && !error && (
        <div className="rounded-md bg-muted/40 p-8 text-center text-sm text-muted-foreground">
          No saved connections yet. Connections are created via the API for now —
          see the ScopeWise docs. Saved secrets are encrypted at rest and never
          shown again.
        </div>
      )}

      {connections !== null && connections.length > 0 && (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Connection</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Last pull</TableHead>
                <TableHead>Health</TableHead>
                <TableHead className="min-w-[220px]">Last error</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {connections.map((c) => (
                <TableRow key={c.connection_id}>
                  <TableCell>
                    <div className="text-sm font-medium">{c.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {c.platform === 'splunk'
                        ? `Splunk · ${c.config.host ?? ''}`
                        : `Sentinel · ${c.config.workspace ?? ''}`}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{scheduleLabel(c)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {c.health.last_pull_at ? (
                      <>
                        {fmtDate(c.health.last_pull_at)}
                        <span className="block">{c.health.last_status}</span>
                      </>
                    ) : (
                      'never'
                    )}
                  </TableCell>
                  <TableCell>
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                        c.health.scheduled_failure_streak === 0
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                          : 'bg-rose-100 text-rose-800 border-rose-200'
                      )}
                    >
                      {c.health.scheduled_failure_streak === 0
                        ? 'Healthy'
                        : `${c.health.scheduled_failure_streak} failed in a row`}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {c.health.last_error ?? '—'}
                    {testResult[c.connection_id] && (
                      <span className="block font-medium text-foreground">
                        {testResult[c.connection_id]}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={testing === c.connection_id}
                      onClick={() => handleTest(c.connection_id)}
                    >
                      {testing === c.connection_id ? 'Testing…' : 'Test'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}
