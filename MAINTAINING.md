# Maintaining the LOD Cloud site

For contributors and the review policy see [CONTRIBUTING.md](CONTRIBUTING.md). This page is about how the site is run.

## Branches

All pull requests go to `main`. A push to `main` publishes the site. The ruleset *Require validation pass to merge* requires a pull request and the `validate` check for `main` and forbids deleting it and force-pushing to it; organisation administrators can bypass it (for bulk imports only).

## Workflows

| Workflow | When | What it does |
|---|---|---|
| **Validate** (`validate.yml`) | pull requests and pushes | The unit tests, then `scripts/validate.py`. On a pull request the files it changes must be fully valid; the rest are checked against `data/known-issues.json`. |
| **Site** (`site.yml`) | pull requests and pushes | Builds the Jekyll site, the data files (`scripts/export_site_data.py`), the search index (Pagefind) and the availability data, downloads the current diagram release, and checks the pages, files and internal links. On a push to `main` the same site is published to GitHub Pages. |
| **Submissions** (`submissions.yml`) | an *Add/Update a dataset* issue is opened or edited | Turns the form into a file, checks it, and opens or updates a pull request, or comments the problems. Uses a GitHub App token, so that Validate runs on the pull request. |
| **Links** (`links.yml`) | Mondays 04:00 UTC, or `gh workflow run links.yml [-f limit=N]` | Checks the download, SPARQL and example URLs (`scripts/check_links.py`), stores the results in `resources.json` on the `link-status` branch, summarises the unavailable datasets and opens issues for archive candidates (`scripts/archive_issues.py`). |
| **Clouds** (`clouds.yml`) | the 1st of the month 03:00 UTC, or `gh workflow run clouds.yml [-f date=yyyy-mm-dd] [-f iterations=N]` | Draws the diagrams (`scripts/generate_clouds.py`), publishes the release `clouds-<date>` and opens a pull request adding it to `site/_data/versions.yml`. |

A pull request that changes `links.yml`, `check_links.py`, `clouds.yml`, `generate_clouds.py` or `cloud-settings/` runs that workflow as a **dry run** (300 URLs, or 100 iterations; nothing is published). The diagram pull request, opened with the default token, does not trigger checks by itself: use **Approve workflows to run** on it. (Using the App token in `clouds.yml` would remove that step.)

Scheduled and manually started workflows only run from the default branch, and workflows that react to issues do too.

## Settings the workflows depend on

- **Pages:** Settings → Pages → Source *GitHub Actions*; the environment `github-pages` may deploy from `main`.
- **Secrets:** `SUBMISSIONS_APP_ID` and `SUBMISSIONS_APP_PRIVATE_KEY`, for the GitHub App `lod-cloud-submissions` (owned by the organisation, installed on this repository only; permissions *Contents* and *Pull requests*: read and write). To replace the key: generate a new one on the App's page and update the secret.
- **Variable:** `PAGES_BASEURL` must be **unset or empty**. Set to a path (for example `/lod-cloud-site`), the build prefixes every link with it and adds `noindex`; that is for previewing at the `github.io` address.
- **Labels:** `add-dataset` and `update-dataset`, used by the forms and checked by the Submissions workflow; `archive-candidate` (created by the Links workflow).

## Hosting

lod-cloud.net is served from GitHub Pages (`https://lod-cloud.github.io/lod-cloud-site/`, the same site; its pages carry a `canonical` link to `lod-cloud.net`) through a reverse proxy that the university runs; its configuration is not kept here. What the site needs from it: `/` maps to the Pages path `/lod-cloud-site/` (the site is built for the root of its host, `PAGES_BASEURL` empty), and the extensionless metadata paths (`/json/`, `/api/`, `/rdf/`, `/ttl/`, `/nt/`, `/extract/datasets`, `/extract/rdf`) get a real `Content-Type`, because Pages sends them as `application/octet-stream`. Moving lod-cloud.net to GitHub Pages by DNS would remove the proxy, but then those paths would need file extensions (#116).

## Things that can go wrong

- **A scheduled run did not happen:** GitHub pauses schedules in a repository without activity for 60 days; any push or a manual run starts them again.
- **Links reports many failures:** some servers block GitHub's addresses and many dead hosts are real (most of the URLs failed in the first full test). Look at `failures` and `failing_since` in `resources.json`, not at one run.
- **The diagram run fails on one domain:** L-BFGS fails on some domains, and the script falls back to steepest descent (it logs this). A failure of both is an error in `lod-cloud-draw`.
- **A dataset page returns 404 for an identifier with a `:`:** these pages are at an encoded path (`/dataset/ISSN%253A0080-3626/`); `404.html` redirects the plain spelling. See `site/README.md`.
- **A submission is not turned into a pull request:** read the Submissions run; the issue gets a comment when the form is invalid, and none when the workflow itself failed (for example an expired App key).

## Retiring the old application

The Java application (`src/`, `pom.xml`, `Dockerfile`, `for-mongo.py`, `src/main/webapp/versions/`) and its container are not used since the move on 2026-11-24. The final `lod-data.json` it served is the starting point of `data/datasets/`. They can be deleted from the repository (history keeps them) and the container removed from the server once rollback is no longer wanted.
