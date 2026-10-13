export function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <h1 className="text-lg font-semibold tracking-tight">ProofCheck</h1>
          <p className="text-sm text-muted">Your statement never leaves this computer.</p>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <p className="text-muted">
          Check UPI payment screenshots against your bank statement.
        </p>
      </main>
    </div>
  );
}
