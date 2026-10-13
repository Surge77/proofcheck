"""Read bank statement exports (CSV / XLS / XLSX) into credit transactions."""

from proofcheck.statements.table import StatementError, parse_statement

__all__ = ["StatementError", "parse_statement"]
