'use client';

import { useState } from 'react';
import axios from 'axios';
import { AlertBanner } from '@/components/app';
import { Button } from '@/components/ui/button';

export function RequestAccessForm({
  source,
  message,
  heading = 'Request access to run assessments',
  defaultEmail = '',
  defaultName = '',
}: {
  source: string;
  message: string;
  heading?: string;
  defaultEmail?: string;
  defaultName?: string;
}) {
  const [name, setName] = useState(defaultName);
  const [email, setEmail] = useState(defaultEmail);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Honeypot is uncontrolled and read from the form at submit time, so a bot
    // that sets input.value directly (bypassing React state) is still caught.
    const website = String(new FormData(e.currentTarget as HTMLFormElement).get('website') || '');
    if (website) {
      setSent(true);
      return;
    }
    setLoading(true);
    setError('');
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/contact`, {
        name,
        email,
        message,
        source,
      });
      setSent(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not submit -- please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-theme font-app max-w-[520px] rounded-[10px] border border-border bg-card p-4">
      {heading && <h2 className="mb-1 text-[15px] font-semibold">{heading}</h2>}
      <p className="mb-3 text-[13px] text-muted-foreground">
        Running a review or assessment is switched on per organisation. Send us your details
        and we will enable it.
      </p>
      {sent ? (
        <p className="text-[13px] text-muted-foreground" role="status">
          Thanks. We will enable assessments for your organisation and email you.
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-3.5">
          <div>
            <label htmlFor="name" className="mb-1 block text-xs font-medium text-muted-foreground">Name</label>
            <input
              id="name"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-accent"
            />
          </div>
          <div>
            <label htmlFor="email" className="mb-1 block text-xs font-medium text-muted-foreground">Work email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-accent"
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
          {error && <AlertBanner kind="error">{error}</AlertBanner>}
          <Button type="submit" disabled={loading} className="h-10 w-full">
            {loading ? 'Sending...' : 'Request access'}
          </Button>
        </form>
      )}
    </div>
  );
}
