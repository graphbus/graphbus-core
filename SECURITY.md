# Security Policy

## Supported Versions

GraphBus is currently in alpha. Security fixes are applied to the latest version only.

| Version | Supported |
|---|---|
| 0.1.x (alpha) | ✅ Current |
| < 0.1.0 | ❌ |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Email us at: **security@graphbus.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

We'll acknowledge receipt within 48 hours and provide a timeline for a fix.

## Scope

### In scope
- Vulnerabilities in `graphbus_core`, `graphbus_cli`, `graphbus_api`, or `graphbus-mcp-server`
- Issues with artifact loading that could allow code execution outside the runtime sandbox
- API server authentication or authorization issues
- LLM prompt injection in the negotiation protocol that could cause unintended code commits

### Out of scope
- Vulnerabilities in your own agent code (GraphBus executes what you write)
- Issues in third-party dependencies (report to those maintainers directly)
- Security issues in LLM providers (Anthropic, OpenAI) — report to them directly

## Security Model

GraphBus's security posture:

**Build Mode:** The build pipeline executes Python code in your project and makes LLM API calls. Treat build-time credentials (API keys) as you would any CI secret. Never commit API keys to source.

**Runtime Mode:** The runtime loads JSON artifacts and calls Python methods you defined. It does not make external network calls unless your agent code does. The runtime is not sandboxed — it has the same access as the process that launched it.

**Artifact Trust:** `.graphbus/` artifacts are JSON files. They are not executed directly — the runtime imports the Python modules they reference. Only run artifacts from sources you trust.

**LLM Negotiation:** During agent builds, the LLM may propose code changes. All proposals are committed as human-readable diffs that you can review before deployment. Use `git diff` after a build to audit any changes.
