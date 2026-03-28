## 2024-05-15 - [Path Traversal in AI Score Extraction]
**Vulnerability:** The AI-generated 'virality_score' field was concatenated directly into file paths without sanitization, allowing an LLM to perform path traversal (e.g., `../`) and write output files to arbitrary locations.
**Learning:** Untrusted output from LLMs must be treated as malicious user input, especially when used in file system operations. The AI output directly controls the payload in `os.path.join`.
**Prevention:** Always sanitize or type-cast AI-generated fields (e.g., stripping non-alphanumeric characters) before using them in file paths or system commands.

## 2024-05-15 - [SSRF Bypass in Discord Webhook Validation]
**Vulnerability:** URL validation for the Discord Webhook setting relied on a weak `url.startswith("https://discord.com/")` check, allowing Server-Side Request Forgery (SSRF). Attackers could bypass it by supplying URLs with malicious hostnames containing the target string as an HTTP Basic Auth credential (e.g., `https://discord.com@attacker.com/`), which `urllib.request` natively follows.
**Learning:** String matching on URLs is fundamentally insecure because it fails to account for the complex internal structure and parsing logic of URIs (like userinfo and port components).
**Prevention:** Always use `urllib.parse.urlparse` to explicitly and securely validate the `scheme`, exact `hostname`, and starting `path` components independently.
