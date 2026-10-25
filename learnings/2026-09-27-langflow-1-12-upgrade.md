# Upgrading LangFlow 1.10 -> 1.12.3 in Docker without losing flows

## Problem (one line)
Upgrade a LangFlow container whose SQLite DB (57 flows, 91MB) lives on a host bind mount, when the new version runs Alembic migrations in place on boot and the old version cannot read a migrated DB.

## Approach (plain steps)
1. **Find the real target.** `latest` on Docker Hub sorted by date is dominated by `1.13.0.devNN` builds. Filtered those out to find the newest stable, `1.12.3`, and confirmed `latest` resolved to the same digest. Never upgrade onto a dev tag by accident.
2. **Make it reversible before touching anything.** Stopped the container first (so no WAL writes mid-copy), then copied the whole config dir, not just `langflow.db`, since `secret_key` lives beside it and a mismatched key silently breaks encrypted fields.
3. **Pin the version in the launcher.** Changed `langflow-up.sh` from `langflowai/langflow:latest` to an `IMAGE` variable pinned to `1.12.3`. With `latest`, any future container recreate silently jumps versions and migrates the DB with no backup taken.
4. **Read the crash, don't retry it.** First boot exited(3) with `ValueError: Username and password must be set` from `setup_superuser`. 1.12.x flipped the `AUTO_LOGIN` default to off, so it now demands superuser credentials that 1.10 defaulted in. Set `LANGFLOW_AUTO_LOGIN=true` explicitly.
5. **Diff the data, don't just count it.** Flow count fell 57 -> 50 and the count alone looked like data loss. Diffing flow *names* against the backup showed 11 bundled starter templates removed and 4 new ones added; every user-authored `AI3X_*` flow survived.
6. **Regression-test the actual artifact.** Re-ran the flow's 8-case suite on 1.12.3, then separately ran the *stored* flow (not a fresh import) to prove the migrated row still executes. Both still report the same flaky count.

## Judgment calls (what was NOT done, why)
- **Did not choose a superuser + password instead of auto-login.** Existing flows are owned by the auto-login user id; switching the auth model risks orphaning them behind a new account. Auto-login also preserves the workflow the user already had. It is a local dev box, so the tradeoff is acceptable, but it is a deliberate choice, not a default.
- **Did not delete the old 1.10.0 image.** It is the other half of the rollback: backup restores the data, the old image restores the runtime.
- **Did not treat the flow-count drop as loss and roll back.** Rolling back on a count alone would have thrown away a working upgrade. The name diff was cheap and settled it.
- **Did not skip the stored-flow run** even though the test suite passed. The suite imports the JSON fresh, so it proves the file works, not that the migrated database row does. Those are different claims.

## Reusable rule
An in-place migration is only as safe as the snapshot you took while the service was stopped; and after any upgrade, diff the *contents* of what changed rather than the count, because a version bump legitimately adds and removes its own bundled data.
