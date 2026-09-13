/**
 * T-701: Login page component
 * Password-free sign-in/sign-up via Google or an emailed one-time code -- no
 * password, no separate signup screen. A new email creates the account
 * on the spot (see app/routers/auth.py::_get_or_create_user).
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (resp: { credential: string }) => void }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

function storeTokensAndRedirect(router: ReturnType<typeof useRouter>, data: any) {
  localStorage.setItem('access_token', data.access_token);
  if (data.refresh_token) {
    localStorage.setItem('refresh_token', data.refresh_token);
  }
  router.push('/dashboard');
}

function GoogleSignInButton({ onError }: { onError: (msg: string) => void }) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) return;

    const handleCredential = async (resp: { credential: string }) => {
      try {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google`,
          { id_token: resp.credential }
        );
        storeTokensAndRedirect(router, response.data);
      } catch (err: any) {
        onError(err.response?.data?.detail || 'Google sign-in failed');
      }
    };

    const render = () => {
      if (!window.google || !buttonRef.current) return;
      window.google.accounts.id.initialize({ client_id: clientId, callback: handleCredential });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'outline',
        size: 'large',
        width: 336,
      });
      setReady(true);
    };

    if (window.google) {
      render();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = render;
    document.body.appendChild(script);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  if (!clientId) return null;

  // Reserve the button's exact footprint while Google's script loads, so
  // the page doesn't jump and the button doesn't pop in late.
  return (
    <div className="relative flex justify-center" style={{ minHeight: 44 }}>
      {!ready && (
        <div
          aria-hidden="true"
          className="absolute inset-x-0 mx-auto flex h-[44px] w-[336px] max-w-full items-center justify-center rounded-lg bg-muted text-[13px] text-ink3 animate-pulse"
        >
          Loading Google sign-in…
        </div>
      )}
      <div ref={buttonRef} className={ready ? '' : 'invisible'} />
    </div>
  );
}

function OtpLogin({ onError }: { onError: (msg: string) => void }) {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [codeRequested, setCodeRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [codeError, setCodeError] = useState('');
  const router = useRouter();

  const requestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    onError('');
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/otp/request`, { email });
      setCodeRequested(true);
    } catch (err: any) {
      onError(err.response?.data?.detail || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (submittedCode: string) => {
    setLoading(true);
    setCodeError('');
    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/otp/verify`,
        { email, code: submittedCode }
      );
      storeTokensAndRedirect(router, response.data);
    } catch {
      setCodeError("That code didn't match. Please try again.");
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  // Auto-submit as soon as all 4 digits are entered -- no separate
  // "Verify" click needed.
  useEffect(() => {
    if (code.length === 4 && !loading) {
      verifyCode(code);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  if (!codeRequested) {
    return (
      <form onSubmit={requestCode}>
        <div>
          <label htmlFor="email" className="sr-only">
            Your email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] text-foreground outline-none transition-[border-color,box-shadow] duration-150 ease-app focus:border-primary focus:ring-[3px] focus:ring-accent"
            required
          />
        </div>
        <Button type="submit" disabled={loading} className="mt-2.5 h-10 w-full">
          {loading ? 'Sending your code...' : 'Email me a sign-in code'}
        </Button>
        <p className="mt-2 text-xs text-ink3">
          We&apos;ll email you a 4-digit code — no password needed.
        </p>
      </form>
    );
  }

  return (
    <div>
      <p className="text-[13.5px]">
        Enter the 4-digit code sent to <strong>{email}</strong>.
      </p>
      <div className="mt-2.5 flex gap-2">
        <input
          type={showCode ? 'text' : 'password'}
          name="one-time-code"
          autoComplete="one-time-code"
          inputMode="numeric"
          pattern="\d{4}"
          maxLength={4}
          value={code}
          onChange={(e) => {
            setCodeError('');
            setCode(e.target.value.replace(/\D/g, '').slice(0, 4));
          }}
          disabled={loading}
          autoFocus
          aria-label="Sign-in code"
          className="h-10 flex-1 rounded-lg border border-input bg-card text-center font-mono text-lg tracking-[.35em] outline-none transition-[border-color,box-shadow] duration-150 ease-app focus:border-primary focus:ring-[3px] focus:ring-accent disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => setShowCode((v) => !v)}
          className="flex h-10 w-10 flex-none items-center justify-center rounded-lg border border-input text-ink3 transition-colors duration-150 hover:bg-muted hover:text-foreground"
          aria-label={showCode ? 'Hide code' : 'Show code'}
        >
          {showCode ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {loading && <p className="mt-1.5 text-xs text-ink3">Verifying...</p>}
      {codeError && (
        <p role="alert" className="mt-1.5 text-xs text-destructive">
          {codeError}
        </p>
      )}
      <button
        type="button"
        className="mt-3 text-[13px] text-primary hover:underline"
        onClick={() => {
          setCodeRequested(false);
          setCode('');
        }}
      >
        Use a different email
      </button>
    </div>
  );
}

export default function LoginPage() {
  const [error, setError] = useState('');

  return (
    <div className="app-theme font-app min-h-screen bg-background flex items-center justify-center p-6">
      <Card className="w-full max-w-[392px] rounded-[10px] border border-border bg-card px-[26px] pb-6 pt-7">
        <div className="mb-[18px] text-center">
          <div className="mb-2.5 flex items-center justify-center">
            <ShieldCheck className="h-[26px] w-[26px] text-primary" />
          </div>
          <h1 className="text-[19px] font-semibold leading-tight tracking-[-0.01em]">ScopeWise</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">Catch contract risk before you sign.</p>
        </div>

        {error && (
          <div role="alert" className="mb-3.5 rounded-lg border border-sev-crit bg-sev-crit-soft px-3.5 py-3 text-[13px] text-sev-crit">
            {error}
          </div>
        )}

        <GoogleSignInButton onError={setError} />

        <div className="my-[18px] flex items-center gap-2.5">
          <span className="h-px flex-1 bg-border" />
          <span className="inline-flex h-[18px] items-center whitespace-nowrap rounded-full border border-input bg-card px-1.5 text-[10.5px] font-medium text-muted-foreground">
            Or sign in with a code
          </span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <OtpLogin onError={setError} />
      </Card>
    </div>
  );
}
