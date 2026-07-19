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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
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

  const validateFile = (f: File): boolean => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    if (!validTypes.includes(f.type)) {
      setError('Only PDF and DOCX files are supported');
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
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>{versionOfDocId ? 'Upload New Version' : 'Upload Document'}</CardTitle>
            <CardDescription>
              {versionOfDocId
                ? 'This file will be linked as the next version of the source document.'
                : 'Upload a SOW, Proposal, or other document for review'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              {/* Project (optional label) -- inherited automatically when uploading a new version */}
              {!versionOfDocId && (
              <div>
                <label htmlFor="projectName" className="block text-sm font-medium mb-2">
                  Project <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                {presetProjectId ? (
                  <div className="flex items-center justify-between px-4 py-2 border border-input rounded-md bg-muted/50">
                    <span>
                      {projectOptions.find((p) => p.project_id === presetProjectId)?.name ??
                        'Selected project'}
                    </span>
                    <button
                      type="button"
                      className="text-sm text-primary hover:underline"
                      onClick={() => setPresetProjectId('')}
                    >
                      Change
                    </button>
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
                      className="w-full px-4 py-2 border border-input rounded-md bg-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors duration-150 ease-out"
                    />
                    <datalist id="project-options">
                      {projectOptions.map((p) => (
                        <option key={p.project_id} value={p.name} />
                      ))}
                    </datalist>
                    <p className="text-xs text-muted-foreground mt-1">
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
                  'border-2 border-dashed rounded-md p-12 text-center cursor-pointer transition-colors duration-150 ease-out',
                  dragActive
                    ? 'border-primary bg-primary/5'
                    : 'border-input hover:bg-muted/50'
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
                <div className="mb-4">
                  <UploadCloud className="mx-auto h-10 w-10 text-muted-foreground" aria-hidden="true" />
                </div>

                <h3 className="text-lg font-medium mb-2">
                  Drag and drop your document
                </h3>
                <p className="text-muted-foreground mb-2">or click to select</p>
                <p className="text-sm text-muted-foreground">PDF or DOCX • up to 50MB</p>

                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileInput}
                  accept=".pdf,.docx"
                  className="hidden"
                  aria-label="Document file"
                  tabIndex={-1}
                />
              </div>

              {/* Selected File */}
              {file && (
                <div className="border border-[#28A745]/30 bg-[#28A745]/10 rounded-md p-4">
                  <p className="text-[#28A745]">
                    <strong>Selected:</strong> {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div role="alert" className="bg-destructive/10 border border-destructive/30 rounded-md p-4">
                  <p className="text-destructive">{error}</p>
                </div>
              )}

              {/* Success Message */}
              {success && (
                <div role="status" className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-md p-4">
                  <p>{success}</p>
                </div>
              )}

              {/* Submit Button */}
              <Button type="submit" disabled={!file || uploading} className="w-full">
                {uploading ? 'Uploading...' : 'Upload Document'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
