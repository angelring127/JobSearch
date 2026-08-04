import crypto from 'crypto';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const COOKIE_NAME = 'jobmap_admin_session';
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 12;

function getAdminPassword() {
  return process.env.ADMIN_PASSWORD || 'dev-admin-password';
}

function getSessionSecret() {
  return process.env.SESSION_SECRET || process.env.ADMIN_PASSWORD || 'dev-session-secret';
}

function sign(payload: string) {
  return crypto.createHmac('sha256', getSessionSecret()).update(payload).digest('hex');
}

function timingSafeEqualText(a: string, b: string) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

export function verifyAdminPassword(password: string) {
  return timingSafeEqualText(password, getAdminPassword());
}

export function verifySessionCookie(value: string | undefined) {
  if (!value) {
    return false;
  }

  const [expiresAtRaw, signature] = value.split('.');
  if (!expiresAtRaw || !signature || !timingSafeEqualText(signature, sign(expiresAtRaw))) {
    return false;
  }

  const expiresAt = Number(expiresAtRaw);
  return Number.isFinite(expiresAt) && expiresAt > Date.now();
}

export async function createAdminSession() {
  const expiresAt = Date.now() + SESSION_MAX_AGE_SECONDS * 1000;
  const payload = String(expiresAt);
  const store = await cookies();

  store.set(COOKIE_NAME, `${payload}.${sign(payload)}`, {
    httpOnly: true,
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
}

export async function clearAdminSession() {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}

export async function isAdminAuthenticated() {
  const store = await cookies();
  return verifySessionCookie(store.get(COOKIE_NAME)?.value);
}

export async function requireAdmin() {
  if (!(await isAdminAuthenticated())) {
    redirect('/admin/login');
  }
}
