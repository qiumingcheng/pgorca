# PostgreSQL-owned Arrow cleanup and nullable operands

The bridge keeps expression nullability separate from value-type identity for
comparison operands and MIN/MAX arguments. A NOT NULL input and a nullable
constant of the same PostgreSQL/Arrow type can be compared. MIN/MAX results
remain nullable, including an empty input. OID, typmod, collation and Arrow/Daft
type identity remain required; Source, InputRef, Project and schema equality
continue to include nullability.

## Ownership during execution and error unwinding

Each input builder registers a callback in its own memory context before it
can allocate libc buffers. The callback only frees and clears those buffers;
normal destruction deletes that context and follows the same cleanup path.
Each imported output batch similarly registers an Arrow release callback in
its own context before adopting C Data. No callback deletes its own context,
calls ExecutorEnd, or raises a PostgreSQL error.

A separate query child context owns the pending source slots and the raw
output pair returned by `dpg_try_next_batch_v1`. Its callback visits only its
own POD storage, never a PlanState or a child builder/output context. The
bridge writes directly into the registered raw-output slot. Successful batch
adoption clears that slot; a validation or allocation error leaves the slot
owned by the query callback. Pending input remains owned here on `DPG_AGAIN`
and transfers only when the bridge clears the release callbacks.

This division matters because PostgreSQL deletes child contexts before the
parent context's callback. A parent callback must not visit a freed builder or
output batch. The transaction ResourceOwner continues to contain only the
Rust vtable and handle: it never refers back into the query context.

TOAST views remember only newly allocated detoast values. After copying, or
before any explicit append error return, these copies are freed. Values still
owned by the tuple slot are never freed by the builder. PostgreSQL ERROR
unwinding owns remaining palloc allocations; no C++ destructor is required.

## Targeted regression sources

- `test/sql/daft_filter.sql` compares NOT NULL/constant and
  NOT NULL/nullable-column results with PostgreSQL and checks Daft selection.
- `test/sql/daft_aggregate.sql` compares NOT NULL int2/int4 MIN/MAX for
  nonempty and empty inputs, while preserving nonzero estimates on the latter.
- `test/sql/daft_arrow.sql` calls the ownership probe: 512 compressed wide
  text/varchar/bytea rows cross 128 batches without resetting the caller's
  context; a later invalid date exercises early-return cleanup. It checks
  that caller memory stays bounded and counts input-builder, output-array and
  output-schema releases for parent deletion and normal explicit destruction.
- `test/sql/daft_errors.sql` injects an error after the first output row in the
  caller, with a partially consumed batch and no ExecutorEnd. It also checks
  pending-input, unadopted-output, partial-initialization and repeated cleanup
  release counts. Reopening in the same session checks handle/fragment recovery.
- `test/sql/daft_cancel.sql` repeats cancellation before a successful retry.

For an external-TOAST integration check, populate wide text/varchar/bytea
columns after `ALTER TABLE ... ALTER COLUMN ... SET STORAGE EXTERNAL`, select
them through a confirmed Daft projection with small `pg_orca.daft_batch_rows`,
and compare rows with Daft disabled. A receiver-disconnect check should consume
one row from a multirow batch and close the client; parent-error cleanup must
not depend on another CustomScan call or on ExecutorEnd.

These sources and expected files were updated by static review only. No
compilation, regression execution, cancellation experiment or memory experiment
was performed for this amendment. Existing deferred capabilities, the unstarted
P2 stability gate and production-admission limits remain unchanged.
