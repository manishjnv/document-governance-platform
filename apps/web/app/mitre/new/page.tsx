'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Download, FileSpreadsheet, Play, ShieldCheck, Trash2, UploadCloud, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ParsePreview } from '../lib';

const MAX_SIZE = 50 * 1024 * 1024;
const USE_CASE_EXTS = ['.xlsx', '.xls', '.csv', '.pdf', '.docx'];
const ENV_EXTS = ['.xlsx', '.xls'];

const INDUSTRIES = [
  'Financial Services', 'Banking', 'Insurance', 'Healthcare', 'Manufacturing',
  'Energy & Utilities', 'Technology', 'Telecommunications', 'Retail & E-commerce',
  'Government & Public Sector', 'Education', 'Transportation & Logistics',
  'Media & Entertainment', 'Professional Services', 'Other',
];
const REGIONS = [
  'North America', 'Europe (EU)', 'United Kingdom', 'Middle East', 'Africa',
  'India', 'Asia-Pacific', 'Latin America', 'Global', 'Other',
];

interface Exclusion {
  target: string;
  reason: string;
}

function DropZone({
  label,
  hint,
  exts,
  file,
  onFile,
  onError,
  required,
}: {
  label: string;
  hint: string;
  exts: string[];
  file: File | null;
  onFile: (f: File | null) => void;
  onError: (msg: string) => void;
  required?: boolean;
}) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (f: File): boolean => {
    if (!exts.some((ext) => f.name.toLowerCase().endsWith(ext))) {
      onError(`${label}: only ${exts.join(', ')} files are supported`);
      return false;
    }
    if (f.size > MAX_SIZE) {
      onError(`${label}: file must be under 50MB`);
      return false;
    }
    return true;
  };

  const accept = (f: File | undefined) => {
    if (f && validate(f)) {
      onFile(f);
      onError('');
    }
  };

  return (
    <div>
      <div className="mb-1.5 text-sm font-medium">
        {label} {required && <span className="text-destructive">*</span>}
      </div>
      {file ? (
        <div className="flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm">
          <span className="flex min-w-0 items-center gap-2 text-emerald-800">
            <FileSpreadsheet size={15} className="shrink-0" aria-hidden="true" />
            <span className="truncate">{file.name}</span>
            <span className="shrink-0 text-xs text-emerald-700/70">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </span>
          </span>
          <button
            type="button"
            aria-label={`Remove ${file.name}`}
            className="text-emerald-800 hover:text-emerald-950"
            onClick={() => {
              onFile(null);
              if (inputRef.current) inputRef.current.value = '';
            }}
          >
            <X size={15} />
          </button>
        </div>
      ) : (
        <div
          role="button"
          tabIndex={0}
          aria-label={`${label}: choose a file or drag it here`}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            accept(e.dataTransfer.files?.[0]);
          }}
          className={cn(
            'cursor-pointer rounded-md border-2 border-dashed p-5 text-center transition-colors duration-150 ease-out',
            dragActive ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
          )}
        >
          <UploadCloud className="mx-auto mb-1.5 h-6 w-6 text-muted-foreground" aria-hidden="true" />
          <p className="text-sm">Drag &amp; drop or click to select</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={exts.join(',')}
        className="hidden"
        tabIndex={-1}
        aria-label={label}
        onChange={(e) => accept(e.target.files?.[0])}
      />
    </div>
  );
}

export default function NewMitreAssessmentPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [useCaseFile, setUseCaseFile] = useState<File | null>(null);
  const [envFile, setEnvFile] = useState<File | null>(null);
  const [industry, setIndustry] = useState('');
  const [region, setRegion] = useState('');
  const [countDisabled, setCountDisabled] = useState(false);
  const [exclusions, setExclusions] = useState<Exclusion[]>([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [preview, setPreview] = useState<ParsePreview | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem('access_token')) router.push('/login');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!useCaseFile) {
      setError('Please add your detection-rule export first');
      return;
    }
    const cleanExclusions = exclusions.filter((x) => x.target.trim() || x.reason.trim());
    if (cleanExclusions.some((x) => !x.target.trim() || !x.reason.trim())) {
      setError('Every scope exclusion needs both a target and a reason');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('use_cases', useCaseFile);
      if (envFile) formData.append('environment', envFile);
      if (name.trim()) formData.append('name', name.trim());
      formData.append(
        'intake',
        JSON.stringify({
          industry: industry || null,
          region: region || null,
          count_disabled_as_coverage: countDisabled,
          exclusions: cleanExclusions.map((x) => ({
            target: x.target.trim(),
            reason: x.reason.trim(),
          })),
        })
      );
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      setPreview(res.data);
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRun = async () => {
    if (!preview) return;
    setRunning(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${preview.assessment_id}/run`,
        null,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      router.push(`/mitre/${preview.assessment_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not start the assessment');
      setRunning(false);
    }
  };

  const columnLabels: Record<string, string> = {
    name: 'Use-case name',
    tags: 'MITRE techniques',
    logic: 'Detection logic',
    description: 'Description',
    log_source: 'Log source',
    enabled: 'Status',
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-lg font-semibold">New MITRE Assessment</h1>

        {/* Privacy notice — shown before any file is chosen (plan §2) */}
        <div className="flex gap-2.5 rounded-md border border-sky-200 bg-sky-50 p-3.5 text-sm text-sky-900">
          <ShieldCheck size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
          <p>
            We never ask for credentials, raw log data, or personal data — upload rule
            metadata and environment inventory only. Files are stored encrypted; only
            minimal rule excerpts are sent for AI tagging.
          </p>
        </div>

        {!preview && (
          <form onSubmit={handleCreate} className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Your files</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <DropZone
                    label="Detection rules export"
                    hint="xlsx, xls, csv, pdf or docx · up to 50MB"
                    exts={USE_CASE_EXTS}
                    file={useCaseFile}
                    onFile={setUseCaseFile}
                    onError={setError}
                    required
                  />
                  <DropZone
                    label="Environment workbook (recommended)"
                    hint="xlsx with Assets, Log Sources, Tooling, Crown Jewels sheets"
                    exts={ENV_EXTS}
                    file={envFile}
                    onFile={setEnvFile}
                    onError={setError}
                  />
                </div>
                <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
                  <a
                    href="/templates/scopewise-mitre-use-cases.xlsx"
                    download
                    className="flex items-center gap-1 text-primary hover:underline"
                  >
                    <Download size={13} aria-hidden="true" /> Use-case template
                  </a>
                  <a
                    href="/templates/scopewise-mitre-environment.xlsx"
                    download
                    className="flex items-center gap-1 text-primary hover:underline"
                  >
                    <Download size={13} aria-hidden="true" /> Environment template
                  </a>
                  <span className="text-muted-foreground">
                    Without the environment workbook we assess the full ATT&CK matrices, so
                    your score reads lower than reality.
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">About this assessment</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div>
                    <label htmlFor="mitre-name" className="mb-1.5 block text-sm font-medium">
                      Assessment name
                    </label>
                    <input
                      id="mitre-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Q3 SOC coverage"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </div>
                  <div>
                    <label htmlFor="mitre-industry" className="mb-1.5 block text-sm font-medium">
                      Industry
                    </label>
                    <select
                      id="mitre-industry"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">Select…</option>
                      {INDUSTRIES.map((i) => (
                        <option key={i} value={i}>{i}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="mitre-region" className="mb-1.5 block text-sm font-medium">
                      Region
                    </label>
                    <select
                      id="mitre-region"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">Select…</option>
                      {REGIONS.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={countDisabled}
                    onChange={(e) => setCountDisabled(e.target.checked)}
                    className="mt-0.5"
                  />
                  <span>
                    Count disabled rules as coverage
                    <span className="block text-xs text-muted-foreground">
                      Off (recommended): a disabled rule scores as “partial” at best, since
                      it isn’t actually alerting today.
                    </span>
                  </span>
                </label>

                <div>
                  <div className="mb-1 text-sm font-medium">Scope exclusions</div>
                  <p className="mb-2 text-xs text-muted-foreground">
                    Tell us what NOT to assess and why — e.g. “mobile: BYOD fleet is
                    unmanaged”, “T1200: accepted risk, physical controls”. Excluded items
                    leave the score entirely, and the report lists them with your reason.
                  </p>
                  <div className="space-y-2">
                    {exclusions.map((x, i) => (
                      <div key={i} className="flex gap-2">
                        <input
                          type="text"
                          value={x.target}
                          aria-label={`Exclusion ${i + 1} target`}
                          onChange={(e) =>
                            setExclusions((prev) =>
                              prev.map((p, j) => (j === i ? { ...p, target: e.target.value } : p))
                            )
                          }
                          placeholder="T1200, mobile, or a platform (e.g. macOS)"
                          className="w-2/5 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                        <input
                          type="text"
                          value={x.reason}
                          aria-label={`Exclusion ${i + 1} reason`}
                          onChange={(e) =>
                            setExclusions((prev) =>
                              prev.map((p, j) => (j === i ? { ...p, reason: e.target.value } : p))
                            )
                          }
                          placeholder="Why it's out of scope (required)"
                          className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                        <button
                          type="button"
                          aria-label={`Remove exclusion ${i + 1}`}
                          onClick={() => setExclusions((prev) => prev.filter((_, j) => j !== i))}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    ))}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => setExclusions((prev) => [...prev, { target: '', reason: '' }])}
                  >
                    Add exclusion
                  </Button>
                </div>
              </CardContent>
            </Card>

            {error && (
              <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3.5 text-sm text-destructive">
                {error}
              </div>
            )}

            <Button type="submit" disabled={!useCaseFile || submitting} className="w-full">
              {submitting ? 'Uploading & parsing…' : 'Upload & preview'}
            </Button>
          </form>
        )}

        {preview && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Parse preview — check before running</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div className="rounded-md bg-muted/40 p-2.5 text-center">
                  <div className="text-lg font-bold">{preview.row_count}</div>
                  <div className="text-[11px] text-muted-foreground">rules found</div>
                </div>
                <div className="rounded-md bg-emerald-50 p-2.5 text-center">
                  <div className="text-lg font-bold text-emerald-700">{preview.tagged}</div>
                  <div className="text-[11px] text-muted-foreground">already tagged</div>
                </div>
                <div className="rounded-md bg-amber-50 p-2.5 text-center">
                  <div className="text-lg font-bold text-amber-700">{preview.untagged}</div>
                  <div className="text-[11px] text-muted-foreground">for AI tagging</div>
                </div>
                <div className="rounded-md bg-rose-50 p-2.5 text-center">
                  <div className="text-lg font-bold text-rose-700">{preview.invalid}</div>
                  <div className="text-[11px] text-muted-foreground">invalid tags</div>
                </div>
              </div>

              {preview.extraction_pending && (
                <p className="rounded-md bg-amber-50 p-3 text-xs text-amber-800">
                  Your document isn&apos;t a spreadsheet, so rules will be AI-extracted from
                  its text when the assessment runs — lower fidelity than the XLSX template.
                </p>
              )}

              {Object.keys(preview.columns).length > 0 && (
                <div>
                  <div className="mb-1 text-xs font-semibold text-muted-foreground">
                    Detected columns{preview.sheet ? ` (sheet “${preview.sheet}”)` : ''} — if
                    these look wrong, fix the headers and re-upload
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(preview.columns).map(([field, idx]) => (
                      <span key={field} className="rounded-full border bg-muted/40 px-2 py-0.5 text-[11px]">
                        {columnLabels[field] ?? field}: column {Number(idx) + 1}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {preview.environment_provided ? (
                <p className="text-xs text-muted-foreground">
                  Environment: {preview.environment.platforms.join(', ') || 'no platforms detected'}
                  {preview.environment.has_ics_assets && ' · OT/ICS assets'}
                  {preview.environment.has_managed_mobile && ' · managed mobile'}
                  {' · sheets: '}
                  {Object.values(preview.sheets_found).join(', ')}
                </p>
              ) : (
                <p className="text-xs text-amber-700">
                  No environment workbook — the full ATT&CK matrices will be assessed, so
                  the score is a lower bound.
                </p>
              )}

              {preview.warnings.length > 0 && (
                <ul className="space-y-1">
                  {preview.warnings.map((w, i) => (
                    <li key={i} className="rounded-md bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
                      {w}
                    </li>
                  ))}
                </ul>
              )}

              {error && (
                <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="flex flex-col gap-2 sm:flex-row">
                <Button onClick={handleRun} disabled={running} className="flex-1">
                  <Play size={15} className="mr-1.5" aria-hidden="true" />
                  {running ? 'Starting…' : 'Run assessment'}
                </Button>
                <Button variant="outline" onClick={() => { setPreview(null); setError(''); }}>
                  Back — change files
                </Button>
              </div>
              <p className="text-center text-[11px] text-muted-foreground">
                <Link href="/mitre" className="hover:underline">
                  Or keep it for later — it&apos;s saved in your assessment list.
                </Link>
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
