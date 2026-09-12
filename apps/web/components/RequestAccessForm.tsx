'use client';

import { useState } from 'react';
import axios from 'axios';

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
    <div className="rounded-lg border p-5">
      {heading && <h2 className="font-semibold mb-1">{heading}</h2>}
      <p className="text-sm text-muted-foreground mb-4">
        Running a review or assessment is switched on per organisation. Send us your details
        and we will enable it.
      </p>
      {sent ? (
        <p className="text-muted-foreground" role="status">
          Thanks. We will enable assessments for your organisation and email you.
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
            {loading ? 'Sending...' : 'Request access'}
          </button>
        </form>
      )}
    </div>
  );
}
