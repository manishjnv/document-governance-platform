'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, Target } from 'lucide-react';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { AssessmentListItem, STATUS_META, fmtDate } from './lib';

export default function MitreListPage() {
  const router = useRouter();
  const [items, setItems] = useState<AssessmentListItem[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => setItems(res.data))
      .catch((err) => {
        if (err.response?.status === 401) router.push('/login');
        else setError(err.response?.data?.detail || 'Failed to load assessments');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <TooltipProvider>
        <div className="mb-4 flex items-center justify-between gap-2">
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <Target size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            MITRE Assessments
          </h1>
          <Button asChild size="sm">
            <Link href="/mitre/new">
              <Plus size={15} className="mr-1" aria-hidden="true" />
              New assessment
            </Link>
          </Button>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {items !== null && items.length === 0 && !error && (
          <div className="rounded-md bg-muted/40 p-8 text-center">
            <Target size={28} className="mx-auto mb-3 text-muted-foreground" aria-hidden="true" />
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              Upload your SIEM detection rules and we&apos;ll show you exactly which MITRE
              ATT&CK techniques you can and can&apos;t detect. You get a coverage score, a
              ranked gap list, and a build roadmap — tailored to the log sources you
              already have.
            </p>
            <Button asChild size="sm" className="mt-4">
              <Link href="/mitre/new">Start your first assessment</Link>
            </Button>
          </div>
        )}

        {items !== null && items.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Coverage</TableHead>
                  <TableHead className="hidden sm:table-cell">ATT&CK</TableHead>
                  <TableHead className="hidden md:table-cell">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => {
                  const status = STATUS_META[item.status] ?? STATUS_META.pending;
                  return (
                    <TableRow
                      key={item.assessment_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/mitre/${item.assessment_id}`)}
                    >
                      <TableCell className="text-sm font-medium">{item.name}</TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                            status.chip
                          )}
                        >
                          {status.label}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.strict_pct !== null ? (
                          <Tooltip delayDuration={150}>
                            <TooltipTrigger asChild>
                              <div className="flex cursor-default items-center gap-2">
                                <span className="w-12 text-sm font-semibold">{item.strict_pct}%</span>
                                <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                                  <div
                                    className="h-full rounded-full bg-primary"
                                    style={{ width: `${Math.min(100, item.strict_pct)}%` }}
                                  />
                                </div>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs text-xs">
                              Strict coverage: techniques with a qualifying detection, out of
                              those applicable to your environment. Weighted (partial counts
                              as half): {item.weighted_pct}%.
                            </TooltipContent>
                          </Tooltip>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                        v{item.attack_version}
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                        {fmtDate(item.created_at)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}
