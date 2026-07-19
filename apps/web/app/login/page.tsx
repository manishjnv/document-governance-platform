/**
 * T-701: Login page component
 * Email/password, Google Sign-In, and email one-time-code login.
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

  return <div ref={buttonRef} className="flex justify-center" />;
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
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-3 py-2 border border-input rounded-md text-sm transition duration-150 ease-out focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          required
        />
        <Button type="submit" variant="outline" disabled={loading} className="w-full">
          {loading ? 'Sending...' : 'Email me a login code'}
        </Button>
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
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOtp, setShowOtp] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Backend expects JSON { email, password } (app/schemas/auth.py::LoginRequest),
      // not an OAuth2-style form-urlencoded username/password body.
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`,
        { email, password }
      );
      storeTokensAndRedirect(router, response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

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

          {showOtp ? (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">Email code</span>
                </div>
              </div>
              <OtpLogin onError={setError} />
              <button
                type="button"
                className="text-sm text-primary hover:underline w-full text-center"
                onClick={() => setShowOtp(false)}
              >
                Use password instead
              </button>
            </>
          ) : (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">Or</span>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2">
                    Email Address
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

                <div>
                  <label htmlFor="password" className="block text-sm font-medium mb-2">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 border border-input rounded-md text-sm transition duration-150 ease-out focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                    required
                  />
                </div>

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>
              </form>

              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => setShowOtp(true)}
              >
                Sign in with an email code instead
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
