# Security policy

## Supported versions

Security fixes are applied to the latest version on the default branch.

## Reporting a vulnerability

Do not publish API keys, session secrets, medical data, or exploit details in a
public issue. Contact the repository owner privately and include reproduction
steps with all secrets redacted.

## Deployment requirements

- Supply credentials at runtime; never bake `.env` into an image.
- Rotate any credential that has appeared in chat, logs, screenshots, commits,
  CI output, or container layers.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Restrict `CORS_ORIGINS` to the deployed origin.
- Keep the service behind authentication and an HTTPS reverse proxy.
- Do not mount or redistribute a corpus without confirmed authorization.

MedAgent is a research and demonstration system, not a medical device and not
a substitute for professional medical advice.
