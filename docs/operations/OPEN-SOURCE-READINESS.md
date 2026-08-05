# Open-Source Readiness

Open-source readiness is a multi-gate maintenance contract, not a visibility
toggle and not a single green CI run.

This repository is already public. The gates below define what must be checked
before broader promotion, a versioned release, or a claim that the public chain
is closed.

## Gates

1. **Current identity and entry surface**
   - README decision card states the current product, phase, authority, and one
     next gate before historical evidence depth.
   - Contributor, support, security, notice, and issue surfaces use the current
     repository identity and URLs.
   - Historical repository names and IDs remain only where evidence identity
     requires them.
2. **Public-data and secret boundary**
   - Scan the tracked tree and Git history for high-confidence credentials,
     private keys, sensitive filenames, private configuration, and restricted
     material without printing suspected secret values.
   - Synthetic detector fixtures must be distinguishable from real secrets.
   - Machine and user paths are minimized in new public evidence. A necessary
     observed path is classified as evidence rather than silently rewritten.
   - Tool absence or a bounded pattern scan is reported as a limitation, not a
     comprehensive secret-scan pass.
3. **Rights and provenance**
   - Repository-owned code, documentation, generated metadata, third-party
     bodies, and official/runtime baselines retain distinct license classes.
   - Exact-upstream candidates are not relicensed or presented as a current
     vendored release.
   - Historical derivatives preserve their original source pins, licenses,
     notices, and immutable evidence bindings.
4. **Reproducibility**
   - `scripts/verify_bootstrap.py`, `scripts/verify.py`, affected unit tests,
     and `git diff --check` pass from the maintained checkout.
   - A clean anonymous clone can read the public repository and run the bounded
     bootstrap verifier at the exact remote revision being claimed.
   - Hosted GitHub Actions are optional corroboration, not a paid acceptance
     dependency.
5. **Live GitHub controls**
   - Recheck visibility, default branch, Issues, security settings, private
     vulnerability reporting, branch rules, Pages, Releases, and community
     profile from the live repository.
   - Documentation must describe unavailable controls honestly. A link to a
     disabled private-reporting surface is not a reporting channel.
   - Enabling repository security or branch settings is an external state
     change and requires separate authority.
6. **Promotion and release**
   - Public visibility does not imply production readiness, endorsement,
     versioned release readiness, candidate value, or cross-host proof.
   - Promotion waits for rights, safety, reproducibility, support, and claim
     boundaries appropriate to the promoted artifact.

## Initial observed baseline on 2026-08-05

The following is a dated observation and must be rechecked before a current
claim:

- `yiheng8023/agent-autonomy-harness` was public with default branch `main` and
  Issues enabled; Wiki and Discussions were disabled.
- GitHub reported secret scanning, non-provider patterns, push protection,
  validity checks, and Dependabot security updates disabled.
- Private vulnerability reporting was disabled. The public issue contact now
  routes to `SECURITY.md` instead of claiming that a private advisory form is
  usable.
- The code-scanning API reported no analysis. No branch protection or
  versioned GitHub Release was established by this audit. GitHub reported a
  100% community profile from the recognized local community files. Pages was
  not configured.
- `gitleaks` was not installed and was not added as a new dependency.
- A bounded high-confidence scan covered the 172 pre-existing reachable commits
  plus the current tracked worktree. It found credential-shaped strings only
  in two secret-detector test fixtures; both strings are synthetic test inputs.
  No private-key, GitHub-token, AWS-key, or Slack-token shape was found by that
  bounded scan.
- The tracked tree contains dated runtime evidence with absolute local paths
  and a numeric Windows profile segment. These paths are not
  credentials, but they are privacy and portability surface. They remain
  classified evidence for now because bulk rewriting would invalidate frozen
  observations and their digests. New evidence should avoid unnecessary paths.

## Minimum live security baseline applied on 2026-08-05

The user separately authorized the bounded live-control change after the
initial observation. GitHub API write responses and independent reads then
reported:

- Dependabot vulnerability alerts and security updates were enabled;
- Secret scanning and push protection were enabled;
- Private vulnerability reporting was enabled and the public entry surfaces
  now route sensitive reports to GitHub's private form;
- `main` branch protection applied to administrators and non-administrators:
  force pushes and branch deletion were blocked. Normal direct pushes remain
  allowed;
- non-provider patterns and validity checks remain disabled; and
- No required pull request, review, status check, or CodeQL workflow was added.

This is a `minimum-live-security-baseline-applied` observation, not a permanent
control guarantee. GitHub settings can drift and must be rechecked for a
current claim. The bounded repository scan remains narrower than a comprehensive
secret-history review, and no paid Actions dependency was introduced.

## Current verdict

`minimum-live-security-baseline-applied-public-chain-partial`

The current tree has a bounded local entrypoint, rights, and high-confidence
secret-history review plus a dated minimum live-control baseline. An anonymous
clean clone must verify each exact pushed revision before it is claimed. The
open-source chain remains partial because this baseline does not establish a
versioned release, comprehensive secret scan, permanent control state, support
commitment, production readiness, or broader promotion readiness.
