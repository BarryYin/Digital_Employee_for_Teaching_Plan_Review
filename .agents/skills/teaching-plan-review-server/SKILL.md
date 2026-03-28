---
name: teaching-plan-review-server
description: Access and verify the deployed Teaching Plan Review app at https://115.190.176.52. Use when asked to inspect the server, check whether the deployed app is reachable, submit a lesson plan remotely, review history/result pages, or explain how an agent should interact with the deployed site over HTTP. For this skill, prefer browserless probing with curl/HTTP first, and explicitly verify whether the app is mounted because the server root may return nginx 404.
---

# Teaching Plan Review Server

Use this skill when working against the deployed server at `https://115.190.176.52`.

## What This Skill Covers

- Verify whether the app is actually exposed on the server
- Interact with the deployed app over HTTP without a browser
- Submit lesson plans to the remote form endpoint
- Follow redirects to review result pages
- Read history and history detail pages
- Distinguish app failures from reverse-proxy/deployment failures

## Current Server Reality

As verified on **2026-03-28**, these HTTPS requests succeeded at the transport layer but returned nginx `404 Not Found` pages:

- `/`
- `/history`
- `/review_result/1`
- `/health`
- `/robots.txt`
- `/.well-known/agent.json`

That means the IP is reachable over HTTPS, but the Flask app is **not currently exposed at those paths**. Do not assume the application is live on root just because the host answers.

## Workflow

### 1. Probe first

Always start with a lightweight probe:

```bash
/usr/bin/curl -I -k https://115.190.176.52
/usr/bin/curl -sS -k https://115.190.176.52 | /usr/bin/sed -n '1,40p'
```

If root or common app routes return an nginx 404 page, say so plainly. Do not pretend the app is usable.

### 2. If the app is mounted, use these routes

The repository’s current Flask routes are:

- `GET /` - lesson plan submission page
- `POST /submit_essay` - submit lesson plan form
- `GET /review_result/<essay_id>` - result page
- `GET /history` - list history
- `GET /history/detail/<essay_id>` - history detail

Read [references/routes.md](references/routes.md) for concrete curl flows.

### 3. Use browserless interaction by default

Prefer `curl` form submissions and HTML inspection over browser automation unless the user explicitly needs visual validation or a JS-only behavior.

### 4. Be precise about failure mode

Classify issues into one of these buckets:

- `transport ok, app not mounted` - HTTPS works but nginx returns 404
- `app reachable, workflow slow` - form submits but result takes 60-120s
- `app reachable, workflow unavailable` - result page shows local fallback review
- `route mismatch` - app may be mounted under another prefix/path

### 5. When reporting status

Include:

- exact URL tested
- exact path tested
- HTTP status
- whether the body is nginx 404 or app HTML
- whether you are making an inference

## Interaction Notes

- The deployed IP currently needs `-k` in curl examples because the host is accessed directly by IP over HTTPS.
- Successful lesson-plan review requests may take more than a minute. Avoid using overly short client timeouts.
- If the app is mounted later under a prefix, adjust every route relative to that prefix before testing form submission.

## What Not To Do

- Do not claim the app is healthy if you only confirmed the host answers HTTPS
- Do not assume `/` is the correct base path when the response body is nginx 404
- Do not guess result payloads without actually following the redirect and inspecting the returned page

