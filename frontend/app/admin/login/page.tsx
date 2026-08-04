import { redirect } from 'next/navigation';
import { isAdminAuthenticated } from '@/lib/server/admin-auth';
import { loginAction } from '../actions';

export const dynamic = 'force-dynamic';

type LoginPageProps = {
  searchParams?: Promise<{ error?: string }>;
};

export default async function AdminLoginPage({ searchParams }: LoginPageProps) {
  if (await isAdminAuthenticated()) {
    redirect('/admin');
  }

  const params = await searchParams;
  const hasError = params?.error === '1';

  return (
    <main className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <form action={loginAction} className="w-full max-w-sm bg-white border border-slate-200 rounded-md p-6 shadow-sm">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-slate-950">JobMap Admin</h1>
          <p className="mt-1 text-sm text-slate-600">운영 비밀번호를 입력하세요.</p>
        </div>

        <label className="block text-sm font-medium text-slate-700" htmlFor="password">
          비밀번호
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950 focus:ring-1 focus:ring-slate-950"
          required
        />

        {hasError && (
          <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            비밀번호가 올바르지 않습니다.
          </p>
        )}

        <button
          type="submit"
          className="mt-5 w-full rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          로그인
        </button>
      </form>
    </main>
  );
}
