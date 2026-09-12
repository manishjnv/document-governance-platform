'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';

type Template = { title: string; desc: string; href: string; format: string };

const STORAGE_KEY = 'scopewise_templates_unlocked';

export function TemplatesGate({ templates }: { templates: Template[] }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'unlocked' | 'error'>('idle');
  const [error, setError] = useState('');

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') setStatus('unlocked');
    } catch {
      // ignore
    }
  }, []);

  const unlock = () => {
    setStatus('unlocked');
    try {
      localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      // ignore
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Honeypot is uncontrolled and read from the form at submit time, so a bot
    // that sets input.value directly (bypassing React state) is still caught.
    const website = String(new FormData(e.currentTarget as HTMLFormElement).get('website') || '');
    if (website) {
      unlock();
      return;
    }
    setLoading(true);
    setError('');
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/contact`, {
        name,
        email,
        message: 'Template download request: ' + templates.map((t) => t.title).join(', '),
        source: 'templates',
      });
      unlock();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not submit -- please try again.');
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const unlocked = status === 'unlocked';

  return (
    <div>
      <ul className="space-y-4 mb-8">
        {templates.map((t) => (
          <li key={t.href} className="rounded-lg border p-5">
            <div className="flex items-start justify-between gap-3 mb-1">
              <h2 className="font-semibold">{t.title}</h2>
              <span className="text-xs rounded-full border px-2 shrink-0">{t.format}</span>
            </div>
            <p className="text-sm text-muted-foreground mb-3">{t.desc}</p>
            {unlocked ? (
              <a
                href={t.href}
                download
                className="text-primary underline hover:no-underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                Download {t.format}
              </a>
            ) : (
              <p className="text-sm text-muted-foreground">Available after you fill in the form below</p>
            )}
          </li>
        ))}
      </ul>

      {unlocked ? (
        <p className="text-muted-foreground" role="status">
          Thanks. The links are live above; the files are yours to keep.
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-1">Name</label>
            <input
              id="name"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border px-3 py-2 bg-background"
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">Work email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border px-3 py-2 bg-background"
            />
          </div>
          <div aria-hidden="true" className="hidden">
            <label htmlFor="website">Website</label>
            <input
              id="website"
              name="website"
              tabIndex={-1}
              autoComplete="off"
              defaultValue=""
            />
          </div>
          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            {loading ? 'Sending...' : 'Get the templates'}
          </button>
        </form>
      )}
    </div>
  );
}
