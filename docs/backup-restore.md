# Backup & Restore Runbook

FRD §9 requirements: automated daily encrypted backups, one copy off-site,
**quarterly restore drills**, RPO ≤ 24h. An untested backup is not a backup.

## Backups

`scripts/backup.sh` dumps the Postgres database (via the compose `db` service),
gzips it, optionally GPG-encrypts it (`BACKUP_GPG_RECIPIENT`), applies local
retention (`BACKUP_RETENTION_DAYS`, default 14), and sanity-checks the output size.

Schedule it daily:

```cron
0 2 * * *  cd /path/to/hms && ./scripts/backup.sh >> backups/backup.log 2>&1
```

**Off-site copy is mandatory.** Sync `backups/` to storage on different hardware
(e.g. `rclone sync backups/ remote:hms-backups`) after each run. For production,
enable GPG encryption — backups contain patient data.

## Restore

```bash
# 1. Decrypt if needed
gpg --decrypt hms_20260713T020000Z.sql.gz.gpg > dump.sql.gz

# 2. Restore into a FRESH database (never overwrite prod directly)
docker compose exec -T db createdb -U hms hms_restore
gunzip -c dump.sql.gz | docker compose exec -T db psql -U hms -d hms_restore

# 3. Verify (see checklist), then swap databases or point DATABASE_URL at it.
```

## Quarterly restore drill checklist

Do this every quarter, on the calendar, no exceptions:

- [ ] Pick the most recent backup from **off-site** storage (not the local copy)
- [ ] Restore into a scratch database following the steps above
- [ ] Row counts: users, clinics, audit log entries match expectations
- [ ] Log into a staging instance pointed at the restored DB
- [ ] Open a patient record end-to-end (Phase 1+): registration → encounter → invoice
- [ ] Record drill date, backup age, time-to-restore, and any failures in this file

| Date | Backup age | Time to restore | Result | Notes |
|------|-----------|-----------------|--------|-------|
|      |           |                 |        |       |
