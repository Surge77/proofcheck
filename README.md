# ProofCheck

**Check UPI payment screenshots against your bank statement, on your own laptop.**

Tuition teachers, housing-society treasurers, home bakers and tiffin services collect payments
by UPI into a personal account. The "proof" arrives as a screenshot on WhatsApp, and every month
someone matches dozens of them against the bank statement by hand. Fake payment screenshots are a
common scam, and they look exactly like real ones.

ProofCheck reads each screenshot with local open-weight models, finds its 12-digit UPI reference
(UTR), and looks for that reference in your bank statement. It then tells you, in plain words,
who really paid.

Nothing is uploaded anywhere. The models run on your machine, uploads stay in memory, and your
bank statement never leaves your laptop.

## What it tells you

| Result | Meaning |
|---|---|
| **Verified** | The UTR is in your statement with the same amount. The money arrived. |
| **Amount differs** | The UTR is there, but the screenshot shows a different amount (edited screenshot, or a part payment). |
| **Not in statement** | No such UTR in this statement. It may be fake, or it may not have settled yet. ProofCheck never says "fake". |
| **Duplicate** | The same UTR was already used by another screenshot: one payment shown twice. |
| **Outside dates** | The screenshot is dated outside the statement's period. Check a newer statement. |
| **Unreadable** | No UTR could be read. Check this one by hand. |

Add an optional roster (`name,amount[,payer][,upi_id]`) to see **who has paid, part paid, only
sent a screenshot, or not paid**. Money counts even if nobody sent a screenshot, because the
statement is the source of truth.

## How it works

```
screenshot ──► RapidOCR ──► exact characters ─┐
     │                                        ├─► cross-check ──► Receipt (high / low confidence)
     └──────► Gemma 3 4B ──► what they mean ──┘                        │
                                                                       ▼
bank statement (CSV/XLS/XLSX) ──► credits with UTR, payer, UPI id ──► reconcile ──► report
roster (optional) ─────────────────────────────────────────────────────────────────► who paid
```

- **Two open models check each other.** OCR (PP-OCR via RapidOCR) sees exact digits but not
  meaning. Gemma 3 4B (via Ollama) understands which number is the UTR, which is the amount, and
  whether the payment succeeded, but it can misread digits. A value is trusted only when OCR saw
  the same characters. "High confidence" means both agree on the UTR and amount, *and* the screen
  text confirms success.
- **Bank statements without column mapping.** It detects SBI, HDFC, ICICI and Kotak exports
  (with a generic fallback), skips the preamble rows, and pulls the UTR, payer and UPI id out of
  each bank's narration format.
- **Deterministic reconciliation.** No model decides a result. The statuses above come from plain
  code with 100% test coverage.

## Privacy and security

- Binds to `127.0.0.1` only. Listening on your network needs `PROOFCHECK_ALLOW_LAN=true`.
- Uploads are parsed **in memory**. Starlette's default spooling of large files to a temp file is
  replaced, and a test fails if anything is ever written to disk.
- Only pages served by ProofCheck itself can call the API (Host and Origin checks block other
  websites and DNS rebinding). One check runs at a time.
- The Ollama URL must be on this machine, and system HTTP proxies are ignored, so screenshots
  can't be routed elsewhere.
- Untrusted-file limits: request size, a decompression-bomb pixel budget, an xlsx zip-bomb check,
  row caps, and CSV export protected against spreadsheet formula injection.
- No UTRs, names or file contents are logged.

These protections came from a security review of the upload path. All ten findings are fixed and
covered by tests.

## Run it

You need [Ollama](https://ollama.com), [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
ollama pull gemma3:4b

cd frontend && npm ci && npm run build && cd ..
cd backend && uv sync && uv run proofcheck
```

Open http://127.0.0.1:8000, drop in screenshots and a statement export, and press **Check
payments**. Without Ollama it still works with OCR only, and every row is marked for checking.

### Try the demo data

`samples/` holds a fictional tuition class's October fees: eight screenshots, an SBI-format
statement and a roster, covering every result above. The screenshots use a made-up "Demo Pay"
app and are watermarked **SAMPLE - NOT A REAL PAYMENT**. A tool that catches fake screenshots
shouldn't ship a kit for making them. Regenerate with `uv run python scripts/make_demo_data.py`.

## Accuracy

`backend/scripts/accuracy.py` measures extraction against hand-labelled real screenshots kept in
the git-ignored `private/` folder. It reports UTR and amount accuracy for the fused pipeline and
for OCR alone, plus the number that matters most: how often a *high-confidence* answer is right.
Output masks every UTR to its last four digits.

On the synthetic demo set, the full pipeline (real OCR and real Gemma) gives the expected result
for all 8 screenshots and all 8 roster lines, in 196 s on a GTX 1650 (4 GB), about 24 s per
screenshot. That proves the pipeline works end to end. It says nothing about accuracy on real
phone screenshots.

Results on real screenshots: *pending*. They'll be published here once measured.

## Development

```bash
cd backend && uv run pytest && uv run pyright && uv run ruff check .
cd frontend && npm run typecheck && npm test
```

The Python 3.11 backend uses FastAPI and Pydantic. The frontend is React 19, TypeScript and
Tailwind. CI runs both on every push.

## Limits

- Bank narration formats follow the public export layouts and still need checking against more
  real exports. Open an issue with an anonymised row if your bank's isn't parsed.
- A UTR missing from the statement isn't proof of fraud: the payment may still be settling.
- Speed depends on your GPU. Without one, Gemma runs on the CPU and is slower.

## License

MIT
