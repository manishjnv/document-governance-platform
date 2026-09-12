'use client';

import { useRef, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { Copy, Download, FileJson, Info, Loader2, UploadCloud, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

const MAX_SIZE = 10 * 1024 * 1024;
const REPORT_EXTS = ['.json', '.sarif', '.zip'];
const MANIFEST_EXTS = ['.json'];

const KIT_VERSION = '1.3.0';

const STEPS = [
  <>
    Unzip the kit, then run <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800 ring-1 ring-inset ring-slate-200">.\setup.cmd</code> (Windows, double-click works) or{' '}
    <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800 ring-1 ring-inset ring-slate-200">setup.sh</code> (macOS/Linux) — it installs the scanner and asks for your OpenRouter key
  </>,
  <>
    Run <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800 ring-1 ring-inset ring-slate-200">.\scopewise-scan.cmd &lt;repo&gt;</code> /{' '}
    <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800 ring-1 ring-inset ring-slate-200">scopewise-scan.sh &lt;repo&gt;</code> — shows the cost estimate, then scans after you confirm
  </>,
  <>Upload the <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800 ring-1 ring-inset ring-slate-200">scopewise-scan-*.zip</code> it produces here</>,
];

function FileRow({ file, onRemove }: { file: File; onRemove: () => void }) {
  const kb = file.size / 1024;
  const size = kb > 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${kb.toFixed(0)} KB`;
  return (
    <div className="flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm">
      <span className="flex min-w-0 items-center gap-2 text-emerald-800">
        <FileJson size={15} className="shrink-0" aria-hidden="true" />
        <span className="truncate">{file.name}</span>
        <span className="shrink-0 text-xs text-emerald-700/70">{size}</span>
      </span>
      <button
        type="button"
        aria-label={`Remove ${file.name}`}
        className="text-emerald-800 hover:text-emerald-950"
        onClick={onRemove}
      >
        <X size={15} />
      </button>
    </div>
  );
}

export default function NewCodeReviewPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [manifestFile, setManifestFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [kitBusy, setKitBusy] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const reportInputRef = useRef<HTMLInputElement>(null);
  const manifestInputRef = useRef<HTMLInputElement>(null);

  const validate = (f: File, exts: string[], label: string): boolean => {
    if (!exts.some((ext) => f.name.toLowerCase().endsWith(ext))) {
      setError(`${label}: only ${exts.join(', ')} files are supported`);
      return false;
    }
    if (f.size > MAX_SIZE) {
      setError(`${label}: file must be under 10 MB`);
      return false;
    }
    return true;
  };

  const acceptReport = (f: File | undefined) => {
    if (!f) return;
    if (validate(f, REPORT_EXTS, 'Scan report')) {
      setReportFile(f);
      setError('');
    }
  };

  const acceptManifest = (f: File | undefined) => {
    if (!f) return;
    if (validate(f, MANIFEST_EXTS, 'Run manifest')) {
      setManifestFile(f);
      setError('');
    }
  };

  const downloadKit = async () => {
    setKitBusy(true);
    setError('');
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/kit.zip`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `scopewise-scan-kit-v${KIT_VERSION}.zip`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError('Could not download the scan kit');
    } finally {
      setKitBusy(false);
    }
  };

  const copyCommand = () => {
    navigator.clipboard.writeText('vvaharness scan --repo /path/to/repo --stop-after s9');
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportFile) {
      setError('Please add your findings.json, .sarif or scan zip file first');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('report', reportFile);
      if (manifestFile) formData.append('manifest', manifestFile);
      if (name.trim()) formData.append('name', name.trim());
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      router.push(`/codereview/${res.data.review_id}`);
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  };

  const footerNote = (
    <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <Info size={13} className="shrink-0" aria-hidden="true" />
      Findings are AI triage candidates from your scan; nothing runs on ScopeWise.
    </p>
  );

  return (
    <AppShell>
      <TooltipProvider>
      <div className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-lg font-semibold">New code security review</h1>

        <div className="grid gap-4 md:grid-cols-2">
          <Card className="rounded-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">1 · Get the scanner</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3.5 p-3.5 pt-0">
              <div className="flex items-center gap-2">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <Button type="button" onClick={downloadKit} disabled={kitBusy} className="gap-1.5">
                      {kitBusy ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : <Download size={14} aria-hidden="true" />}
                      Download scan kit
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="text-xs">Zip with the scanner, setup + run scripts and README (~1 MB). Unzip it, do not pip install it.</TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      VVAH v{KIT_VERSION}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="text-xs">Pinned Visa Vulnerability Agentic Harness release inside the kit</TooltipContent>
                </Tooltip>
              </div>

              <ol className="space-y-2 text-sm text-slate-800">
                {STEPS.map((step, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-medium text-primary">
                      {i + 1}
                    </span>
                    <span className="pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="h-px flex-1 bg-border" />
                or run VVAH directly
                <div className="h-px flex-1 bg-border" />
              </div>

              <div className="relative">
                <pre className="overflow-x-auto rounded-md bg-muted/60 p-3 pr-9 font-mono text-xs">
                  <code>vvaharness scan --repo /path/to/repo --stop-after s9</code>
                </pre>
                <button
                  type="button"
                  aria-label="Copy command"
                  onClick={copyCommand}
                  className="absolute right-2 top-2 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <Copy size={14} aria-hidden="true" />
                </button>
                {copied && (
                  <span className="absolute right-9 top-2.5 text-[11px] text-primary">Copied</span>
                )}
              </div>

              <a
                href="https://github.com/visa/visa-vulnerability-agentic-harness"
                target="_blank"
                rel="noreferrer"
                className="inline-block text-xs text-primary hover:underline"
              >
                Visa Vulnerability Agentic Harness
              </a>

              <div className="hidden md:block">{footerNote}</div>
            </CardContent>
          </Card>

          <Card className="rounded-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">2 · Upload the results</CardTitle>
            </CardHeader>
            <CardContent className="p-3.5 pt-0">
              <form onSubmit={handleSubmit} className="space-y-3.5">
                <div>
                  <label htmlFor="review-name" className="mb-1.5 block text-sm font-medium">
                    Name <span className="font-normal text-muted-foreground">(optional)</span>
                  </label>
                  <input
                    id="review-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Q3 backend security scan"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </div>

                <div>
                  {reportFile ? (
                    <FileRow file={reportFile} onRemove={() => {
                      setReportFile(null);
                      if (reportInputRef.current) reportInputRef.current.value = '';
                    }} />
                  ) : (
                    <div
                      role="button"
                      tabIndex={0}
                      aria-label="Scan report: choose a file or drag it here"
                      onClick={() => reportInputRef.current?.click()}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          reportInputRef.current?.click();
                        }
                      }}
                      onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
                      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                      onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
                      onDrop={(e) => {
                        e.preventDefault();
                        setDragActive(false);
                        acceptReport(e.dataTransfer.files?.[0]);
                      }}
                      className={cn(
                        'cursor-pointer rounded-md border-2 border-dashed p-5 text-center transition-colors',
                        dragActive ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
                      )}
                    >
                      <UploadCloud className="mx-auto mb-1.5 h-6 w-6 text-muted-foreground" aria-hidden="true" />
                      <p className="text-sm text-slate-800">Drag &amp; drop or click to select</p>
                      <p className="mt-0.5 text-xs text-slate-600">
                        findings.json, .sarif or the scan zip · up to 10 MB
                      </p>
                    </div>
                  )}
                  <input
                    ref={reportInputRef}
                    type="file"
                    accept={REPORT_EXTS.join(',')}
                    className="hidden"
                    tabIndex={-1}
                    aria-label="Scan report"
                    onChange={(e) => acceptReport(e.target.files?.[0])}
                  />
                  {error && (
                    <p role="alert" className="mt-1.5 text-xs text-destructive">
                      {error}
                    </p>
                  )}
                </div>

                <div>
                  {manifestFile ? (
                    <FileRow file={manifestFile} onRemove={() => {
                      setManifestFile(null);
                      if (manifestInputRef.current) manifestInputRef.current.value = '';
                    }} />
                  ) : (
                    <button
                      type="button"
                      onClick={() => manifestInputRef.current?.click()}
                      className="w-full rounded-md border border-dashed border-input px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/50"
                    >
                      + Add run_manifest_*.json (optional)
                    </button>
                  )}
                  <input
                    ref={manifestInputRef}
                    type="file"
                    accept={MANIFEST_EXTS.join(',')}
                    className="hidden"
                    tabIndex={-1}
                    aria-label="Run manifest"
                    onChange={(e) => acceptManifest(e.target.files?.[0])}
                  />
                </div>

                <div className="flex justify-end">
                  <Button
                    type="submit"
                    disabled={!reportFile || submitting}
                    className="w-full gap-1.5 md:w-auto"
                  >
                    {submitting ? (
                      <>
                        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                        Parsing…
                      </>
                    ) : (
                      'Import and review →'
                    )}
                  </Button>
                </div>
              </form>

              <div className="mt-3.5 md:hidden">{footerNote}</div>
            </CardContent>
          </Card>
        </div>
      </div>
      </TooltipProvider>
    </AppShell>
  );
}
