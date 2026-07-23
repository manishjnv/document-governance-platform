/**
 * T-701: Login page component
 * Seamless sign-in/sign-up via Google or an emailed one-time code -- no
 * password, no separate signup screen. A new email creates the account
 * on the spot (see app/routers/auth.py::_get_or_create_user).
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

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
          className="absolute inset-x-0 mx-auto flex h-[44px] w-[336px] max-w-full items-center justify-center rounded-md border bg-muted/40 text-sm text-muted-foreground animate-pulse"
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
    onError('');
    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/otp/verify`,
        { email, code: submittedCode }
      );
      storeTokensAndRedirect(router, response.data);
    } catch (err: any) {
      onError(err.response?.data?.detail || 'Incorrect code -- please try again');
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
      <form onSubmit={requestCode} className="space-y-3">
        <div>
          <label htmlFor="email" className="block text-sm font-medium mb-2">
            Your email address
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-3 py-2 border border-input rounded-md text-sm transition duration-150 ease-out focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
            required
          />
        </div>
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Sending your code...' : 'Email me a sign-in code'}
        </Button>
        <p className="text-xs text-muted-foreground text-center">
          We&apos;ll email you a 4-digit code — no password needed.
        </p>
      </form>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Enter the 4-digit code sent to <strong>{email}</strong>.
      </p>
      <div className="relative">
        <input
          type={showCode ? 'text' : 'password'}
          inputMode="numeric"
          pattern="\d{4}"
          maxLength={4}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 4))}
          placeholder="1234"
          disabled={loading}
          autoFocus
          className="w-full px-3 py-2 pr-10 border border-input rounded-md text-lg tracking-[0.5em] text-center transition duration-150 ease-out focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => setShowCode((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          aria-label={showCode ? 'Hide code' : 'Show code'}
        >
          {showCode ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {loading && <p className="text-xs text-muted-foreground text-center">Verifying...</p>}
      <button
        type="button"
        className="text-sm text-primary hover:underline w-full text-center"
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
    <div className="min-h-screen bg-muted flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-1">
          <div className="flex items-center justify-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <CardTitle>ScopeWise</CardTitle>
          </div>
          <CardDescription>Catch contract risk before you sign.</CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <div role="alert" className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <p className="text-destructive text-sm">{error}</p>
            </div>
          )}

          <GoogleSignInButton onError={setError} />

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">Or sign in with a code</span>
            </div>
          </div>

          <OtpLogin onError={setError} />
        </CardContent>
      </Card>
    </div>
  );
}
