# Security notes

- Never commit `.env`, API keys, production secrets, database files, or user data.
- If a key was committed accidentally, revoke it at its provider immediately; deleting the file in a later commit is not enough.
- Production must use unique `DJANGO_SECRET_KEY`, `NEXORA_ENCRYPTION_KEY`, HTTPS, correct `DJANGO_ALLOWED_HOSTS`, and trusted CSRF origins.
- Keep `NEXORA_ENCRYPTION_KEY` backed up securely. Losing or changing it makes stored API keys unreadable.
- Report reproducible security issues privately to the project maintainer before publishing technical details.
