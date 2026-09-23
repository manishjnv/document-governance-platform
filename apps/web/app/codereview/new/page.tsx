'use client';

import { useRef, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { Copy, Download, FileJson, Info, Loader2, UploadCloud, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { PageHeader, Chip, AlertBanner } from '@/components/app';
import { cn } from '@/lib/utils';

const MAX_SIZE = 10 * 1024 * 1024;
const REPORT_EXTS = ['.json', '.sarif', '.zip'];
const MANIFEST_EXTS = ['.json'];

const KIT_VERSION = '1.4.0';

// Stage names and limits from VVAH's docs/architecture.md; revisit on each kit upgrade.
const ABOUT_SCANNER = [
  {
    title: 'What it is',
    items: [
      "Visa's open-source AI code scanner (VVAH, Apache-2.0)",
      'Runs on your machine; AI calls go through your own OpenRouter key',
      'Your code is sent to the AI model provider, never to ScopeSense',
      'Reports vulnerabilities only; the kit does not change your code',
    ],
  },
  {
    title: 'Stages',
    items: [
      'Map: source-to-sink call graph, repo survey, threat model',
      'Split: the code is cut into focused review chunks',
      'Review: AI deep-dive per chunk, then evidence gates',
      'Verify: adversarial true/false-positive check and CVSS score',
      'Rank: duplicates merged, exploit chains linked, report + SARIF',
    ],
  },
  {
    title: 'What it finds',
    items: [
      'Auth and access-control gaps, injection, SSRF, path traversal',
      'Weak crypto and certificate checks, secrets in logs, logic bugs',
      'CI/CD and infrastructure-as-code risks',
      'Each finding: CWE, CVSS, exploit scenario, fix and verification note',
    ],
  },
  {
    title: 'Limits',
    items: [
      'Findings are AI triage candidates: confirm before acting',
      'Deepest data-flow tracing for Python, Java, C#, JS/TS; lighter for Go',
      'No branch- or path-sensitive analysis',
      'Large repos take hours and millions of tokens; the kit estimates cost first',
      'Exploit chains need findings.json; a .sarif upload has none',
    ],
  },
];

const STEPS = [
  <>
    Unzip the kit, then run <code className="rounded-md border border-border bg-muted/50 px-1 font-mono text-xs">.\setup.cmd</code> (Windows, double-click works) or{' '}
    <code className="rounded-md border border-border bg-muted/50 px-1 font-mono text-xs">setup.sh</code> (macOS/Linux) — it installs the scanner and asks for your OpenRouter key
  </>,
  <>
    Run <code className="rounded-md border border-border bg-muted/50 px-1 font-mono text-xs">.\scopewise-scan.cmd &lt;repo&gt;</code> /{' '}
    <code className="rounded-md border border-border bg-muted/50 px-1 font-mono text-xs">scopewise-scan.sh &lt;repo&gt;</code> — shows the cost estimate, then scans after you confirm
  </>,
  <>Upload the <code className="rounded-md border border-border bg-muted/50 px-1 font-mono text-xs">scopewise-scan-*.zip</code> it produces here</>,
];

function FileRow({ file, onRemove }: { file: File; onRemove: () => void }) {
  const kb = file.size / 1024;
  const size = kb > 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${kb.toFixed(0)} KB`;
  return (
    <div className="flex items-center gap-2 rounded-lg border border-ok bg-ok-soft px-2.5 py-2 text-[13px] text-ok">
      <FileJson size={15} className="shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate">{file.name}</span>
      <span className="shrink-0 tabular-nums">{size}</span>
      <button
        type="button"
        aria-label={`Remove ${file.name}`}
        className="shrink-0 text-ok hover:opacity-75"
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
      Findings are AI triage candidates from your scan; nothing runs on ScopeSense.
    </p>
  );

  return (
    <AppShell>
      <TooltipProvider>
      <div className="mx-auto max-w-3xl space-y-4">
        <PageHeader title="New code security review" />

        <div className="grid gap-4 md:grid-cols-2 [&>*]:min-w-0">
          <div className="rounded-[10px] border border-border bg-card">
            <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
              <h3 className="text-sm font-semibold">1 · Get the scanner</h3>
            </div>
            <div className="space-y-3.5 p-4">
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
                <Chip tone="neutral" xs tip="Pinned Visa Vulnerability Agentic Harness release inside the kit">
                  VVAH v{KIT_VERSION}
                </Chip>
              </div>

              <ol className="space-y-2 text-sm text-foreground [overflow-wrap:anywhere]">
                {STEPS.map((step, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft text-[11px] font-medium text-primary">
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
                <pre className="overflow-auto rounded-lg border border-border bg-muted/50 p-3 pr-9 font-mono text-xs leading-[1.55]">
                  <code>vvaharness scan --repo /path/to/repo --stop-after s9</code>
                </pre>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      aria-label="Copy command"
                      onClick={copyCommand}
                      className="absolute right-2 top-2 h-7 w-7 p-0"
                    >
                      <Copy size={14} aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="text-xs">Copy command</TooltipContent>
                </Tooltip>
                {copied && (
                  <span className="absolute right-11 top-2.5 text-[11px] text-primary">Copied</span>
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
            </div>
          </div>

          <div className="rounded-[10px] border border-border bg-card">
            <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
              <h3 className="text-sm font-semibold">2 · Upload the results</h3>
            </div>
            <div className="p-4">
              <form onSubmit={handleSubmit} className="space-y-3.5">
                <div>
                  <label htmlFor="review-name" className="mb-1 block text-xs font-medium text-muted-foreground">
                    Name <span className="font-normal">(optional)</span>
                  </label>
                  <input
                    id="review-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Q3 backend security scan"
                    className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-accent"
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
                        'cursor-pointer rounded-[10px] border-2 border-dashed px-4 py-[26px] text-center text-muted-foreground transition-[border-color,background-color] duration-150 ease-app',
                        dragActive ? 'border-primary bg-accent-soft' : 'border-line2 hover:bg-muted/60'
                      )}
                    >
                      <UploadCloud className="mx-auto mb-1.5 h-[26px] w-[26px] text-ink3" aria-hidden="true" />
                      <p className="text-sm">Drag &amp; drop or click to select</p>
                      <p className="mt-0.5 text-xs">
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
                    <AlertBanner kind="error" className="mt-1.5">
                      {error}
                    </AlertBanner>
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
                      className="w-full rounded-lg border border-dashed border-line2 px-2.5 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/60"
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
                    className="h-10 w-full gap-1.5 max-[760px]:w-full md:w-auto"
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
            </div>
          </div>
        </div>

        <section aria-labelledby="about-scanner" className="rounded-[10px] border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <h3 id="about-scanner" className="text-sm font-semibold">About the scanner</h3>
          </div>
          <div className="grid gap-x-6 gap-y-4 p-4 md:grid-cols-2 [&>*]:min-w-0">
            {ABOUT_SCANNER.map((group) => (
              <div key={group.title}>
                <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {group.title}
                </p>
                <ul className="list-disc space-y-1 pl-4 text-[13px] leading-snug text-foreground marker:text-muted-foreground">
                  {group.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </div>
      </TooltipProvider>
    </AppShell>
  );
}
