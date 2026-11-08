-- P0-006-C: lazy Bridge loader failure policy and preload isolation.
-- The helper creates two native shared-library fixtures in this run's private
-- build directory; it never loads either fixture in the postmaster.
SELECT pg_backend_pid() AS loader_backend_pid \gset
\setenv PG_ORCA_LOADER_BACKEND_PID :loader_backend_pid
\getenv loader_fixture_dir PG_ORCA_LOADER_FIXTURE_DIR
\set loader_not_present :loader_fixture_dir '/not_present.so'
\set loader_missing_symbol :loader_fixture_dir '/missing_symbol.so'
\set loader_abi_mismatch :loader_fixture_dir '/abi_major_mismatch.so'
\! python3 "$PG_ORCA_TEST_DIR/helpers/daft_loader.py" setup

SET pg_orca.enable_orca = on;

-- auto: an absent file must silently disable Daft for this plan while ORCA
-- still returns and executes its PostgreSQL alternative.
SET pg_orca.daft_bridge_library = :'loader_not_present';
SET pg_orca.daft_enable = auto;
SELECT count(*) >= 0 AS auto_missing_library_ok FROM pg_class;

-- force: the same condition must become a stable, redacted diagnostic.
SET pg_orca.daft_enable = force;
SELECT oid FROM pg_class LIMIT 1;

-- A library with only one exported ABI symbol must not publish a partial
-- vtable.  auto remains safe; force reports the exact compatibility reason.
SET pg_orca.daft_bridge_library = :'loader_missing_symbol';
SET pg_orca.daft_enable = auto;
SELECT count(*) >= 0 AS auto_missing_symbol_ok FROM pg_class;
SET pg_orca.daft_enable = force;
SELECT oid FROM pg_class LIMIT 1;

-- All symbols are present, but ABI major 2 is incompatible with pg_orca v1.
SET pg_orca.daft_bridge_library = :'loader_abi_mismatch';
SET pg_orca.daft_enable = auto;
SELECT count(*) >= 0 AS auto_abi_mismatch_ok FROM pg_class;
SET pg_orca.daft_enable = force;
SELECT oid FROM pg_class LIMIT 1;

-- shared_preload_libraries=pg_orca must still leave the postmaster without a
-- Bridge mapping or Daft/Tokio thread after child backends exercised failures.
\! python3 "$PG_ORCA_TEST_DIR/helpers/daft_loader.py" assert-preload

RESET pg_orca.daft_enable;
RESET pg_orca.daft_bridge_library;
RESET pg_orca.enable_orca;
