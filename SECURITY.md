# Security policy

## Supported versions

Security fixes are intended for the latest released version on the default branch.

## Reporting a vulnerability

Do not report vulnerabilities in public issues. Contact KavachED maintainers privately through the repository's security advisory or a trusted project contact. Include affected version, impact, reproduction steps, and any suggested mitigation. Please allow maintainers time to investigate before public disclosure.

## Scope

In-scope areas include authentication, workspace/student data isolation, document uploads, SQL access, secrets handling, and dependencies. Do not access, alter, or retain real student information while testing.

## Current safeguards and limitations

Passwords use salted PBKDF2-HMAC-SHA256; repeated failures trigger a temporary lockout; database statements are parameterized; and workspace IDs are part of app queries. Student access is restricted to the linked roll number. Optional Groq and OAuth credentials must be stored as environment variables or deployment secrets.

This app is a hackathon-ready prototype. SQLite deployment storage, lack of audit logging, and a simple session auth model are not a substitute for a production security assessment. Do not deploy with real student data without institutional privacy, access-control, retention, and incident-response review.
