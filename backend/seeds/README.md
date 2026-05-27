# SQL Seed Files

This folder stores SQL data-only seed exports from the current `student_retention` MySQL database.

Files:

- `schema.sql`
  - database schema for the current `student_retention` MySQL database
- `users_seed.sql`
  - seeded admin and faculty login rows from the `users` table
- `project_seed.sql`
  - project data rows from:
    - `students`
    - `lms_activity`
    - `financial`
    - `subject_attendance`
    - `predictions`
    - `interventions`
    - `intervention_history`
    - `alert_history`
    - `password_reset_otps`

`schema.sql` contains structure.
`users_seed.sql` and `project_seed.sql` are data-only dumps.

Example import:

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p student_retention < backend/seeds/schema.sql
mysql -h 127.0.0.1 -P 3306 -u root -p student_retention < backend/seeds/users_seed.sql
mysql -h 127.0.0.1 -P 3306 -u root -p student_retention < backend/seeds/project_seed.sql
```

Recommended order:

1. create database
2. import `schema.sql`
3. import `users_seed.sql`
4. import `project_seed.sql`
5. run backend if you want app-level init checks/fixes
