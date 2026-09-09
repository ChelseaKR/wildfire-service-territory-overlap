# Security

## Reporting

Report a vulnerability through GitHub private vulnerability reporting on this repository.
Acknowledgment target is 72 hours. Please do not open a public issue for a security
report.

## What this project is, in security terms

An offline command-line tool over two public datasets. It has no server, no accounts, no
network listener, and no runtime that anyone else operates. It opens a socket in exactly
two places, `src/wildfire_service_territory_overlap/acquire.py` and
`src/wildfire_service_territory_overlap/refresh.py`, both of which are run by hand and
never from a build or CI.

This section said "exactly one place" for a day after the second one landed, because
nothing read it. A test now derives the set from the modules that import a network reader
and refuses this file if it names a different one.

## The parts worth attacking

- **`src/wildfire_service_territory_overlap/acquire.py`** is where a remote host is read
  for the records this project measures. It pins the
  scheme to HTTPS, sends a User-Agent naming the project, stops on 401, 403 and 429
  rather than routing around them, and refuses a response that is not JSON. There is no
  fallback path and no retry under a different identity.
- **`src/wildfire_service_territory_overlap/refresh.py`** reads a remote host too, and it
  is the newer of the two. `--check` asks each layer for its own record count and asks
  ArcGIS Online for the two territory items' metadata; `--run` performs the acquisition
  above and then builds and compares. Both go through the same pinned reader, so the four
  refusals in the bullet above apply unchanged: there is no fetch and no copy of any
  refusal in this module. What it adds is that a 200 carrying no readable answer is
  reported as unmeasurable rather than as nothing having changed.
- **`src/wildfire_service_territory_overlap/artifacts.py`** decides what is allowed to be written. A change that
  weakens a rule there is a change to what this project will publish about somebody.
- **`src/wildfire_service_territory_overlap/sources.py`** holds the reviewed endpoints. A change to a URL there
  points the acquisition somewhere new.

`.github/CODEOWNERS` routes all three.

## Data handling

The CAL FIRE retrieval is structure-level. Site addresses, parcel numbers and assessed
values are published by CAL FIRE and are deliberately never requested; a test asserts
that. Coordinates are requested, are used only to answer which polygon a point is in,
are never written to a published artifact, and a test refuses an artifact containing one.
`data/raw/` is gitignored.

## Supply chain

Dependencies are locked in `uv.lock` and installed with `uv sync --locked`. One
dependency, `perimeter`, is a git reference pinned to a full commit SHA. GitHub Actions
are pinned to full commit SHAs with the version in a trailing comment. Workflows declare
`permissions: contents: read` at the top level and widen only where a job needs it.
`pip-audit`, `gitleaks`, `semgrep`, `zizmor` and CodeQL run in CI.

## Severity convention

This project operates nothing, so severity here is about what a defect could publish or
sign rather than about uptime.

**Critical**
Anything that could put structure-level data into an artifact: coordinates, addresses,
parcel numbers, assessed values, or any per-record listing. Also: anything that weakens
release tag verification against `.github/allowed_signers`.

**High**
A bypass of a publication rule in `src/wildfire_service_territory_overlap/artifacts.py`; acquisition code that
retries under another identity or routes around an access control; a workflow that
writes credentials somewhere pull-request builds can read.

**Medium**
A nondeterminism that could make two runs of the same inputs disagree silently; a
weakened acquisition completeness check; a supply-chain pin downgraded to a mutable ref.

**Low**
Everything else, including tooling and documentation defects that cannot move a
published figure.

The convention exists so triage is arithmetic instead of negotiation. A report that
does not fit a level still gets answered within the acknowledgment target above.

## If a secret lands in the repository

1. **Revoke and rotate first.** Treat the secret's authority as gone the moment it was
   pushed, whatever happens to the history. Rotation is the fix; rewriting history is
   tidying afterwards.
2. **If it is the release-signing key**, rotate the key, update `.github/allowed_signers`
   through review, and re-verify every existing tag before the next release dispatch.
   The release workflow refuses a signature it cannot verify, which is the behaviour
   you want during a rotation.
3. **Then remove it from history** where the hosting allows, knowing forks and caches
   may retain it anyway. This step is why step 1 comes first.
4. **Write down what leaked, where, and when it was rotated** in the private security
   advisory that tracked the report. If any published figure could have been produced
   under the compromised credential, say so in `PROVENANCE.md`.
