## 2024-05-24 - AI-Driven Path Traversal
**Vulnerability:** The AI-generated 'virality_score' field was concatenated directly into file paths without sanitization, allowing an LLM to perform path traversal (e.g., `../`) and write output files to arbitrary locations.
**Learning:** Untrusted output from LLMs must be treated as malicious user input, especially when used in file system operations. The AI output directly controls the payload in `os.path.join`.
**Prevention:** Always sanitize or type-cast AI-generated fields (e.g., stripping non-alphanumeric characters) before using them in file paths or system commands.
## 2024-05-24 - SSRF via URL Validation Bypass
**Vulnerability:** The application used `url.startswith("https://discord.com/")` to validate Discord webhook URLs before making an HTTP POST request. This is vulnerable to Server-Side Request Forgery (SSRF) bypasses via credential/subdomain manipulation (e.g., `https://discord.com@attacker.com/`), which starts with the required string but resolves to `attacker.com`.
**Learning:** Using simple string matching (like `str.startswith()`) for URL validation is fundamentally insecure because it fails to properly parse the URL components according to RFC standards.
**Prevention:** Always use `urllib.parse.urlparse` to explicitly verify the `scheme`, `hostname`, and `path` of user-provided URLs before making external network requests.
