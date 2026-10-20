# Phase 6 Progress Report: Browser Extension (Chrome & Edge)

**Date:** October 20, 2026  
**Status:** Implementation and automated validation complete; manual Chrome/Edge validation remains  
**Phase:** 6 of 6

## Delivered

- Added opt-in cookie forwarding. Cookie access is an optional extension permission, and website access is requested for only the HTTP(S) host open when the user grants access.
- Added a separate consent toggle for sending cookies and the download referrer. With the toggle disabled or host permission absent, the extension does not read or send cookies.
- The extension cancels the browser download only after the local bridge accepts it. Rejected captures leave the browser download running.
- Connected the bridge to Seadot's download manager and streaming engine. Files are written to a temporary file and atomically moved to the destination after a successful transfer.
- Removed sensitive request headers from download and history database records. The downloader also strips Cookie, Authorization, Proxy-Authorization, and Referer headers when a redirect changes origin.
- Corrected SQLAlchemy status serialization to use the lowercase status values used by the existing database service, and added a startup conversion for existing uppercase enum names.

## Validation

- Extension syntax checks: `node --check` for the service worker and popup scripts.
- Extension tests: 8 passed, covering consent, permission absence, refusal behavior, and bridge handoff.
- Backend tests: 29 passed across Phase 6 handoff/download tests, database model tests, API integration tests, and downloader tests.
- The end-to-end backend test transfers a file from a local HTTP server through the bridge and download manager, and verifies the cookie is not persisted in download or history records.
- Python 3.15 reported one existing Starlette deprecation warning about `httpx`; tests passed.

## Remaining Manual Verification

Load the unpacked extension in Chrome and Edge, grant and revoke permission for a test site, and verify:

1. With Auto-capture disabled, a browser download remains unchanged.
2. With Auto-capture enabled and cookies disabled, Seadot receives the download without cookies.
3. With cookies enabled and per-site permission granted, the download is transferred by Seadot.
4. A rejected bridge request does not cancel the browser download.

The phase remains open until that browser-specific permission and lifecycle check is completed.
