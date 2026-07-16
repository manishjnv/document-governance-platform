/**
 * T-702: Upload page with drag-and-drop
 * Document upload interface with file validation
 */

'use client';

import { useState, useRef } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [orgId, setOrgId] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

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
      setError('Please enter organization ID');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/upload?org_id=${orgId}`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setSuccess(`Document uploaded successfully: ${response.data.filename}`);
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
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Document</h1>
          <p className="text-gray-600 mb-8">Upload a SOW, Proposal, or other document for review</p>

          <form onSubmit={handleUpload} className="space-y-6">
            {/* Organization ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Organization ID
              </label>
              <input
                type="text"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                placeholder="Enter your organization UUID"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>

            {/* Drag and Drop Area */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-12 text-center transition cursor-pointer ${
                dragActive
                  ? 'border-purple-500 bg-purple-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="mb-4">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-8-12v12m0 0l-3-3m3 3l3-3"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Drag and drop your document
              </h3>
              <p className="text-gray-600 mb-2">or click to select</p>
              <p className="text-sm text-gray-500">PDF or DOCX • up to 50MB</p>

              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileInput}
                accept=".pdf,.docx"
                className="hidden"
              />
            </div>

            {/* Selected File */}
            {file && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800">
                  <strong>Selected:</strong> {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800">{error}</p>
              </div>
            )}

            {/* Success Message */}
            {success && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800">{success}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
