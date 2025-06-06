
## Build
```bash
echo "No build step required for SQL procedures"
```

## Test
```bash
echo "No tests defined"
```

## Lint
```bash
echo "No lint step defined"
```

## Deploy
```bash
echo "Deploy procedures using your SQL Server tools"
```
=======
# Overview
This directory holds the SQL Server stored procedures executed by the EnergieApp notebooks. Editing these scripts adjusts the queries and data logic used by the dashboards. Key files: `usp_GetConnectionDataFull.sql`, `usp_GetMinMaxPeriodForEAN.sql` and their *_OnlyLDNODN variants.

# Dev Environment Setup
Stored procedures run on a SQL Server instance. Use SSMS or `sqlcmd` to deploy them:
```bash
sqlcmd -S <server> -d <db> -i usp_GetConnectionDataFull.sql
```
Replace `<server>` and `<db>` with your environment.

# Testing & Linting
- Validate syntax by executing scripts in a test database.
- Optionally integrate tSQLt or a similar framework for unit tests.

# Contribution Guidelines
- Comment complex logic inline with `--` notes.
- Keep transaction handling and error messages consistent.

# PR Instructions
- Use commit titles like `feat(sql): <summary>` or `fix(sql): <summary>`.
- Prefix PR titles with `[SQL]` and describe which procedures changed.
