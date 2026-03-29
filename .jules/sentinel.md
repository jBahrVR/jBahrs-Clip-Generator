## 2024-05-24 - AI-Driven Path Traversal
**Vulnerability:** The AI-generated 'virality_score' field was concatenated directly into file paths without sanitization, allowing an LLM to perform path traversal (e.g., `../`) and write output files to arbitrary locations.
**Learning:** Untrusted output from LLMs must be treated as malicious user input, especially when used in file system operations. The AI output directly controls the payload in `os.path.join`.
**Prevention:** Always sanitize or type-cast AI-generated fields (e.g., stripping non-alphanumeric characters) before using them in file paths or system commands.
## 2024-05-24 - Webhook SSRF via startswith() Bypass
**Vulnerability:** URL validation for Discord webhooks in `app.py` relied on `url.startswith("https://discord.com/")`. This could be bypassed using credential inclusion (e.g., `https://discord.com@attacker.com/`) or domain manipulation, leading to a Server-Side Request Forgery (SSRF) vulnerability.
**Learning:** String matching methods like `startswith()` are fundamentally insecure for URL validation because they do not understand URL structure (scheme, netloc, path) and can be easily deceived by manipulating the authority/credentials section.
**Prevention:** Always use a dedicated URL parsing library like `urllib.parse.urlparse()` to explicitly check the `scheme`, `hostname`, and `path` instead of relying on string matching for URL whitelists.
