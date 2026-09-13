/**
 * T-702: Upload page with drag-and-drop
 * Document upload interface with file validation
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { UploadCloud } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { PageHeader, Chip, AlertBanner } from '@/components/app';
import { cn } from '@/lib/utils';

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [orgId, setOrgId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectOptions, setProjectOptions] = useState<{ project_id: string; name: string }[]>([]);
  const [presetProjectId, setPresetProjectId] = useState('');
  const [versionOfDocId, setVersionOfDocId] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    const preset = search.get('project_id');
    if (preset) setPresetProjectId(preset);
    const versionOf = search.get('version_of');
    if (versionOf) setVersionOfDocId(versionOf);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setOrgId(res.data.org_id);
        axios
          .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`, {
            headers: { Authorization: `Bearer ${token}` },
            params: { org_id: res.data.org_id },
          })
          .then((r) => setProjectOptions(r.data))
          .catch(() => {});
      })
      .catch(() => setError('Failed to load user info'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
        setError('');
      }
    }
  };

  const validTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/csv',
  ];
  const validExtensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv'];

  const validateFile = (f: File): boolean => {
    const maxSize = 50 * 1024 * 1024; // 50MB
    // Some browsers/OSes report an empty or generic MIME type for
    // .doc/.csv -- fall back to the extension so a real supported file
    // isn't rejected client-side (the backend still re-validates by MIME).
    const hasValidExtension = validExtensions.some((ext) =>
      f.name.toLowerCase().endsWith(ext)
    );

    if (!validTypes.includes(f.type) && !hasValidExtension) {
      setError('Only PDF, DOCX, DOC, XLSX, XLS, and CSV files are supported');
      return false;
    }

    if (f.size > maxSize) {
      setError('File size must be less than 50MB');
      return false;
    }

    return true;
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
        setError('');
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file');
      return;
    }

    if (!orgId) {
      setError('Unable to determine your organization -- try refreshing the page');
      return;
    }

    if (!versionOfDocId && !presetProjectId && !projectName.trim()) {
      setError('Choose an existing project or type a new project name');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', file);

      let uploadUrl: string;
      if (versionOfDocId) {
        uploadUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${versionOfDocId}/versions`;
      } else {
        const params = new URLSearchParams({ org_id: orgId });
        if (presetProjectId) {
          params.append('project_id', presetProjectId);
        } else if (projectName) {
          params.append('project_name', projectName);
        }
        uploadUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/upload?${params.toString()}`;
      }

      const response = await axios.post(uploadUrl, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      setSuccess(
        versionOfDocId
          ? `Uploaded as version ${response.data.version}`
          : `Document uploaded successfully: ${response.data.filename}`
      );
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        router.push('/dashboard');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <PageHeader
          title={versionOfDocId ? 'Upload New Version' : 'Upload Document'}
          back={{ href: '/dashboard', label: 'Back to SOW Review' }}
        />
        <div className="rounded-[10px] border border-border bg-card p-4">
          <form onSubmit={handleUpload} className="space-y-3.5">
            <p className="text-[13px] text-muted-foreground">
              {versionOfDocId
                ? 'This file will be linked as the next version of the source document.'
                : 'Upload a SOW, Proposal, or other document for review'}
            </p>

            {/* Project (optional label) -- inherited automatically when uploading a new version */}
            {!versionOfDocId && (
            <div>
              <label htmlFor="projectName" className="mb-1 block text-xs font-medium text-muted-foreground">
                Project <span className="text-sev-crit">*</span>
              </label>
              {presetProjectId ? (
                <div className="flex items-center gap-2">
                  <Chip tone="neutral">
                    {projectOptions.find((p) => p.project_id === presetProjectId)?.name ??
                      'Selected project'}
                  </Chip>
                  <Button type="button" variant="outline" size="sm" onClick={() => setPresetProjectId('')}>
                    Change
                  </Button>
                </div>
              ) : (
                <>
                  <input
                    id="projectName"
                    type="text"
                    list="project-options"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Select existing or type a new project name"
                    className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] outline-none transition-[border-color,background-color] duration-150 ease-app focus:border-primary focus:ring-[3px] focus:ring-accent"
                  />
                  <datalist id="project-options">
                    {projectOptions.map((p) => (
                      <option key={p.project_id} value={p.name} />
                    ))}
                  </datalist>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Pick an existing project from the list, or type a new name to create one.
                  </p>
                </>
              )}
            </div>
            )}

            {/* Drag and Drop Area */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={cn(
                'cursor-pointer rounded-[10px] border-2 border-dashed px-4 py-[26px] text-center text-muted-foreground transition-[border-color,background-color] duration-150 ease-app',
                dragActive
                  ? 'border-primary bg-accent-soft'
                  : 'border-line2 hover:bg-muted/60'
              )}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              aria-label="Choose a document to upload, or drag and drop it here"
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
            >
              <UploadCloud className="mx-auto mb-2 h-[26px] w-[26px] text-ink3" aria-hidden="true" />

              <h3 className="mb-1 text-[15px] font-medium text-foreground">
                Drag and drop your document
              </h3>
              <p className="mb-1 text-muted-foreground">or click to select</p>
              <p className="text-[13px] text-muted-foreground">PDF, DOCX, DOC, XLSX, XLS, or CSV • up to 50MB</p>

              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileInput}
                accept=".pdf,.docx,.doc,.xlsx,.xls,.csv"
                className="hidden"
                aria-label="Document file"
                tabIndex={-1}
              />
            </div>

            {/* Selected File */}
            {file && (
              <div className="flex items-center gap-2 rounded-lg border border-ok bg-ok-soft px-2.5 py-2 text-[13px] text-ok">
                <span className="min-w-0 flex-1 truncate">
                  <strong>Selected:</strong> {file.name}
                </span>
                <span className="tabular-nums whitespace-nowrap">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            )}

            {/* Error Message */}
            {error && <AlertBanner kind="error">{error}</AlertBanner>}

            {/* Success Message */}
            {success && <AlertBanner kind="ok">{success}</AlertBanner>}

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={
                !file ||
                uploading ||
                (!versionOfDocId && !presetProjectId && !projectName.trim())
              }
              className="h-10 w-full"
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
