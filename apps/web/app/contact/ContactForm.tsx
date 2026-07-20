'use client';

import { useState } from 'react';
import axios from 'axios';

export function ContactForm() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'sent' | 'error'>('idle');
  const [error, setError] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/contact`, { name, email, message });
      setStatus('sent');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send -- please try again.');
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  if (status === 'sent') {
    return (
      <p className="text-center text-muted-foreground">
        Thanks -- we&apos;ll get back to you soon.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium mb-1">Name</label>
        <input
          id="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-md border px-3 py-2 bg-background"
        />
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border px-3 py-2 bg-background"
        />
      </div>
      <div>
        <label htmlFor="message" className="block text-sm font-medium mb-1">Message</label>
        <textarea
          id="message"
          required
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="w-full rounded-md border px-3 py-2 bg-background"
        />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 disabled:opacity-50"
      >
        {loading ? 'Sending...' : 'Send message'}
      </button>
    </form>
  );
}
