'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Columns3, Download, FileSpreadsheet, Play, ShieldCheck, Trash2, UploadCloud, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ParsePreview, UseCaseItem } from '../lib';
import { RuleListPanel } from '../components/RuleListPanel';

const MAX_SIZE = 50 * 1024 * 1024;
const USE_CASE_EXTS = ['.xlsx', '.xls', '.csv', '.pdf', '.docx'];
const ENV_EXTS = ['.xlsx', '.xls'];

const INDUSTRIES = [
  'Financial Services', 'Banking', 'Insurance', 'Healthcare', 'Manufacturing',
  'Energy & Utilities', 'Technology', 'Telecommunications', 'Retail & E-commerce',
  'Government & Public Sector', 'Education', 'Transportation & Logistics',
  'Media & Entertainment', 'Professional Services',
  // Plan phase A8 (2026-08-03): added alongside new curated threat profiles
  // in data/threat_profiles.json so these are actually selectable.
  'Hospitality & Food Service', 'Pharmaceuticals & Life Sciences',
  'Agriculture & Food Production', 'Mining & Metals', 'Aerospace & Defense',
  'Construction & Engineering', 'Maritime & Shipping',
  'Other',
];
// Phase A8: free-text suggestions only (not a fixed enum) -- matches the
// 5 curated region_profiles (ranking.build_threat_profile) plus a few
// legacy options kept for continuity. Any text is accepted; an unmatched
// region is a no-op, never an error.
const REGION_SUGGESTIONS = [
  'North America', 'Europe', 'Asia-Pacific', 'Middle East & Africa',
  'Latin America', 'United Kingdom', 'India', 'Global',
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
  // Phase 14b: parse-preview tiles drill into the matching uploaded rows.
  const [rulePanel, setRulePanel] = useState<{
    title: string;
    rules: UseCaseItem[];
  } | null>(null);
  const [running, setRunning] = useState(false);
  const [adjustOpen, setAdjustOpen] = useState(false);
  // field -> 0-based column index; '' = not mapped
  const [colMap, setColMap] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState(false);
  // Phase 14d: optional project metadata (display-only; rides the intake)
  const [projectName, setProjectName] = useState('');
  const [scopeLabel, setScopeLabel] = useState('');
  const [preparedBy, setPreparedBy] = useState('');
  const [purposeNote, setPurposeNote] = useState('');
  // Phase A12: customer/engagement label — scopes the trend block to
  // same-customer runs. Manual for uploads; auto-derived server-side for
  // Sentinel pulls (from the connection/workspace), so this is upload-only.
  const [customer, setCustomer] = useState('');
  // Phase 11: curated threat-actor catalog + selection (optional intake)
  const [actorCatalog, setActorCatalog] = useState<
    { name: string; attack_id: string | null; note: string | null }[]
  >([]);
  const [threatActors, setThreatActors] = useState<string[]>([]);
  // Phase 13a: rule source — upload a file, or pull from Microsoft Sentinel
  const [source, setSource] = useState<'upload' | 'sentinel'>('upload');
  const [siem, setSiem] = useState({
    tenant_id: '',
    client_id: '',
    subscription_id: '',
    resource_group: '',
    workspace: '',
  });
  const [siemSecret, setSiemSecret] = useState('');

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/threat-catalog`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      .then((res) => setActorCatalog(res.data.actors ?? []))
      .catch(() => {}); // optional intake — the wizard works without it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleActor = (actor: string) =>
    setThreatActors((prev) =>
      prev.includes(actor) ? prev.filter((a) => a !== actor) : [...prev, actor]
    );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (source === 'upload' && !useCaseFile) {
      setError('Please add your detection-rule export first');
      return;
    }
    if (source === 'sentinel') {
      const missing = Object.entries(siem).filter(([, v]) => !v.trim());
      if (missing.length > 0 || !siemSecret.trim()) {
        setError('Please fill in every Sentinel connection field, including the client secret');
        return;
      }
    }
    const cleanExclusions = exclusions.filter((x) => x.target.trim() || x.reason.trim());
    if (cleanExclusions.some((x) => !x.target.trim() || !x.reason.trim())) {
      setError('Every scope exclusion needs both a target and a reason');
      return;
    }
    const intake = {
      industry: industry || null,
      region: region || null,
      threat_actors: threatActors,
      count_disabled_as_coverage: countDisabled,
      exclusions: cleanExclusions.map((x) => ({
        target: x.target.trim(),
        reason: x.reason.trim(),
      })),
      // Phase 14d: optional project metadata — makes the report
      // self-identifying when it's forwarded around.
      project_name: projectName.trim() || null,
      scope_label: scopeLabel.trim() || null,
      prepared_by: preparedBy.trim() || null,
      purpose_note: purposeNote.trim() || null,
    };

    setSubmitting(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      let res;
      if (source === 'sentinel') {
        // Phase 13a: token-at-trigger pull — the secret rides this one
        // request and is never stored anywhere.
        res = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/from-siem`,
          {
            platform: 'sentinel',
            config: {
              tenant_id: siem.tenant_id.trim(),
              client_id: siem.client_id.trim(),
              subscription_id: siem.subscription_id.trim(),
              resource_group: siem.resource_group.trim(),
              workspace: siem.workspace.trim(),
            },
            secret: siemSecret,
            ...(name.trim() ? { name: name.trim() } : {}),
            intake,
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSiemSecret('');
      } else {
        const formData = new FormData();
        formData.append('use_cases', useCaseFile as File);
        if (envFile) formData.append('environment', envFile);
        if (name.trim()) formData.append('name', name.trim());
        if (customer.trim()) formData.append('customer', customer.trim());
        formData.append('intake', JSON.stringify(intake));
        res = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`,
          formData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'multipart/form-data',
            },
          }
        );
      }
      setPreview(res.data);
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError(err.response?.data?.detail || (source === 'sentinel' ? 'Sentinel pull failed' : 'Upload failed'));
    } finally {
      setSubmitting(false);
    }
  };

  // Phase 14b: fetch the rows behind a parse-preview tile (rows exist as
  // soon as the assessment is created; empty for pdf/docx extraction dumps).
  const openRuleTile = async (title: string, mappingStatus: string | null) => {
    if (!preview) return;
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${preview.assessment_id}/use-cases`,
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
          params: {
            limit: 500,
            ...(mappingStatus ? { mapping_status: mappingStatus } : {}),
          },
        }
      );
      setRulePanel({ title, rules: res.data.items });
    } catch {
      // non-fatal: the tile stays informational
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

  const openAdjust = () => {
    if (!preview) return;
    const initial: Record<string, string> = {};
    for (const field of Object.keys(columnLabels)) {
      initial[field] = field in preview.columns ? String(preview.columns[field]) : '';
    }
    setColMap(initial);
    setAdjustOpen(true);
  };

  const handleApplyColumns = async () => {
    if (!preview) return;
    setApplying(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const columns: Record<string, number> = {};
      for (const [field, idx] of Object.entries(colMap)) {
        if (idx !== '') columns[field] = Number(idx);
      }
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${preview.assessment_id}/remap`,
        { columns },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPreview(res.data);
      setAdjustOpen(false);
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError(err.response?.data?.detail || 'Could not apply the column mapping');
    } finally {
      setApplying(false);
    }
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
            <div className="flex gap-1 rounded-md border p-1" role="tablist" aria-label="Rule source">
              {(
                [
                  ['upload', 'Upload a file'],
                  ['sentinel', 'Pull from Microsoft Sentinel'],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={source === key}
                  onClick={() => setSource(key)}
                  className={
                    source === key
                      ? 'flex-1 rounded bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary'
                      : 'flex-1 rounded px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground'
                  }
                >
                  {label}
                </button>
              ))}
            </div>

            {source === 'sentinel' && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Microsoft Sentinel connection</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Read-only pull of your analytics rules via a service principal with the{' '}
                    <span className="font-medium">Microsoft Sentinel Reader</span> role.
                    The client secret is used once for this pull and is{' '}
                    <span className="font-medium">never stored</span>.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(
                      [
                        ['tenant_id', 'Tenant ID (GUID)'],
                        ['client_id', 'Client ID (GUID)'],
                        ['subscription_id', 'Subscription ID (GUID)'],
                        ['resource_group', 'Resource group'],
                        ['workspace', 'Log Analytics workspace'],
                      ] as const
                    ).map(([field, label]) => (
                      <div key={field}>
                        <label htmlFor={`siem-${field}`} className="mb-1.5 block text-sm font-medium">
                          {label}
                        </label>
                        <input
                          id={`siem-${field}`}
                          type="text"
                          value={siem[field]}
                          onChange={(e) => setSiem((prev) => ({ ...prev, [field]: e.target.value }))}
                          autoComplete="off"
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                      </div>
                    ))}
                    <div>
                      <label htmlFor="siem-secret" className="mb-1.5 block text-sm font-medium">
                        Client secret <span className="font-normal text-muted-foreground">(never stored)</span>
                      </label>
                      <input
                        id="siem-secret"
                        type="password"
                        value={siemSecret}
                        onChange={(e) => setSiemSecret(e.target.value)}
                        autoComplete="off"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    This path doesn&apos;t take an environment workbook yet, so the whole
                    ATT&amp;CK matrix set is assessed — the score reads lower than reality.
                  </p>
                </CardContent>
              </Card>
            )}

            <Card className={source === 'sentinel' ? 'hidden' : undefined}>
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
                <p className="text-xs text-muted-foreground">
                  If one device sends more than one kind of log, list each log type as its
                  own row in Log Sources — &quot;Infoblox - DNS logs&quot; and &quot;Infoblox
                  - SSH logs&quot; — so each stream gets credited separately.
                </p>
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
                    <input
                      id="mitre-region"
                      type="text"
                      list="mitre-region-suggestions"
                      value={region}
                      onChange={(e) => setRegion(e.target.value.slice(0, 200))}
                      placeholder="e.g. North America"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    <datalist id="mitre-region-suggestions">
                      {REGION_SUGGESTIONS.map((r) => (
                        <option key={r} value={r} />
                      ))}
                    </datalist>
                  </div>
                </div>

                {/* Phase A12: scopes the trend block to the same customer's
                    runs. Manual for uploads; auto-derived from the Sentinel
                    connection/workspace name for pulled assessments. */}
                <div>
                  <label htmlFor="mitre-customer" className="mb-1.5 block text-sm font-medium">
                    Customer / engagement{' '}
                    <span className="font-normal text-muted-foreground">(optional)</span>
                  </label>
                  {source === 'sentinel' ? (
                    <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
                      Auto-set from your Sentinel connection so scheduled re-runs group correctly.
                    </p>
                  ) : (
                    <input
                      id="mitre-customer"
                      type="text"
                      maxLength={200}
                      value={customer}
                      onChange={(e) => setCustomer(e.target.value)}
                      placeholder="e.g. Acme Corp"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    Compares this run&apos;s trend only against the same customer&apos;s previous runs.
                  </p>
                </div>

                {/* Phase 14d: optional project metadata — shown on the
                    assessment header and report covers, so a forwarded
                    report identifies itself. */}
                <div className="grid gap-4 sm:grid-cols-3">
                  {(
                    [
                      ['mitre-project', 'Organization / project', projectName, setProjectName, 'e.g. Contoso Bank SOC'],
                      ['mitre-scope', 'Department or scope', scopeLabel, setScopeLabel, 'e.g. EMEA production estate'],
                      ['mitre-prepared', 'Prepared by', preparedBy, setPreparedBy, 'e.g. Jane Doe, Security Engineering'],
                    ] as const
                  ).map(([id, label, value, setter, placeholder]) => (
                    <div key={id}>
                      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
                        {label}{' '}
                        <span className="font-normal text-muted-foreground">(optional)</span>
                      </label>
                      <input
                        id={id}
                        type="text"
                        maxLength={200}
                        value={value}
                        onChange={(e) => setter(e.target.value)}
                        placeholder={placeholder}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                    </div>
                  ))}
                </div>
                <div>
                  <label htmlFor="mitre-purpose" className="mb-1.5 block text-sm font-medium">
                    Purpose{' '}
                    <span className="font-normal text-muted-foreground">(optional)</span>
                  </label>
                  <textarea
                    id="mitre-purpose"
                    maxLength={500}
                    rows={2}
                    value={purposeNote}
                    onChange={(e) => setPurposeNote(e.target.value)}
                    placeholder="e.g. Annual detection-coverage review for the audit committee"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </div>

                {actorCatalog.length > 0 && (
                  <div>
                    <div className="mb-1.5 block text-sm font-medium">
                      Threat actors of concern{' '}
                      <span className="font-normal text-muted-foreground">(optional)</span>
                    </div>
                    <p className="mb-2 text-xs text-muted-foreground">
                      Pick any groups you track or worry about — gaps in techniques
                      they use will be prioritized in your roadmap. This never
                      changes your coverage score, only the ordering.
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {actorCatalog.map((actor) => (
                        <button
                          key={actor.name}
                          type="button"
                          onClick={() => toggleActor(actor.name)}
                          title={actor.note ?? undefined}
                          aria-pressed={threatActors.includes(actor.name)}
                          className={
                            threatActors.includes(actor.name)
                              ? 'rounded-full border border-primary bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary'
                              : 'rounded-full border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground'
                          }
                        >
                          {actor.name}
                          {actor.attack_id ? ` · ${actor.attack_id}` : ''}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

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
              {/* Phase 14b: each tile opens the matching uploaded rows. */}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(
                  [
                    {
                      value: preview.row_count,
                      label: `rule${preview.row_count === 1 ? '' : 's'} found`,
                      status: null,
                      box: 'bg-muted/40',
                      accent: '',
                    },
                    {
                      value: preview.tagged,
                      label: 'already tagged',
                      status: 'customer_tagged',
                      box: 'bg-emerald-50',
                      accent: 'text-emerald-700',
                    },
                    {
                      value: preview.untagged,
                      label: 'for AI tagging',
                      status: 'unmapped',
                      box: 'bg-amber-50',
                      accent: 'text-amber-700',
                    },
                    {
                      value: preview.invalid,
                      label: `invalid tag${preview.invalid === 1 ? '' : 's'}`,
                      status: 'invalid',
                      box: 'bg-rose-50',
                      accent: 'text-rose-700',
                    },
                  ] as const
                ).map((tile) => (
                  <button
                    key={tile.label}
                    type="button"
                    onClick={() =>
                      openRuleTile(
                        `${tile.value} ${tile.label}`,
                        tile.status
                      )
                    }
                    className={cn(
                      'rounded-md p-2.5 text-center transition-colors hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      tile.box
                    )}
                    title="Click to see these rows"
                  >
                    <div className={cn('text-lg font-bold', tile.accent)}>{tile.value}</div>
                    <div className="text-[11px] text-muted-foreground">{tile.label}</div>
                  </button>
                ))}
              </div>

              {preview.extraction_pending && (
                <p className="rounded-md bg-amber-50 p-3 text-xs text-amber-800">
                  Your document isn&apos;t a spreadsheet, so rules will be AI-extracted from
                  its text when the assessment runs — lower fidelity than the XLSX template.
                </p>
              )}

              {Object.keys(preview.columns).length > 0 && (
                <div>
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-muted-foreground">
                      Detected columns{preview.sheet ? ` (sheet “${preview.sheet}”)` : ''}
                    </span>
                    {preview.headers.length > 0 && !adjustOpen && (
                      <Button type="button" variant="outline" size="sm" onClick={openAdjust}>
                        <Columns3 size={13} className="mr-1" aria-hidden="true" /> Adjust columns
                      </Button>
                    )}
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

              {adjustOpen && preview.headers.length > 0 && (
                <div className="space-y-3 rounded-md border bg-muted/20 p-3">
                  <p className="text-xs text-muted-foreground">
                    Map each field to the right column of your file, then apply — we
                    re-read the uploaded file with your mapping. Only the name column is
                    required.
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(columnLabels).map(([field, label]) => (
                      <div key={field}>
                        <label htmlFor={`col-${field}`} className="mb-0.5 block text-[11px] font-medium">
                          {label}
                          {field === 'name' && <span className="text-destructive"> *</span>}
                        </label>
                        <select
                          id={`col-${field}`}
                          value={colMap[field] ?? ''}
                          onChange={(e) =>
                            setColMap((prev) => ({ ...prev, [field]: e.target.value }))
                          }
                          className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <option value="">— not mapped —</option>
                          {preview.headers.map((h, i) => (
                            <option key={i} value={String(i)}>
                              {i + 1}: {h || '(blank header)'}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                  {preview.sample_rows.length > 0 && (
                    <div className="overflow-x-auto rounded-md border bg-background">
                      <table className="w-full text-[11px]">
                        <thead>
                          <tr>
                            {preview.headers.map((h, i) => (
                              <th key={i} className="whitespace-nowrap border-b bg-muted/40 px-2 py-1 text-left font-medium">
                                {h || `col ${i + 1}`}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.sample_rows.map((row, ri) => (
                            <tr key={ri}>
                              {row.map((cell, ci) => (
                                <td key={ci} className="max-w-56 truncate whitespace-nowrap border-b px-2 py-1 text-muted-foreground">
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleApplyColumns}
                      disabled={applying || (colMap.name ?? '') === ''}
                    >
                      {applying ? 'Re-parsing…' : 'Apply mapping'}
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => setAdjustOpen(false)}>
                      Cancel
                    </Button>
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

        <RuleListPanel
          title={rulePanel?.title ?? null}
          subtitle={
            preview?.extraction_pending
              ? 'Rows from PDF/DOCX documents are AI-extracted when the assessment runs, so this list may be empty until then.'
              : null
          }
          rules={rulePanel?.rules ?? []}
          onClose={() => setRulePanel(null)}
        />
      </div>
    </AppShell>
  );
}
