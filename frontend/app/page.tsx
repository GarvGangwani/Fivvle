export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-4 py-16">
      <div className="text-center">
        <h1 className="mb-3 text-5xl font-bold tracking-tight text-gray-900">
          Fivvle
        </h1>
        <p className="text-xl text-gray-500">
          Validate your startup idea with real signal.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <a
          href="/signup"
          className="w-full rounded-lg bg-gray-900 px-8 py-3 text-center text-sm font-semibold text-white shadow-sm transition-colors hover:bg-gray-700 sm:w-auto"
        >
          Get started
        </a>
        <a
          href="/login"
          className="w-full rounded-lg border border-gray-300 px-8 py-3 text-center text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 sm:w-auto"
        >
          Log in
        </a>
      </div>
    </main>
  );
}
