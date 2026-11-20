# Dataset data

**This is a snapshot, not yet the live data.** Until the site moves to GitHub Pages (#105) the old server remains authoritative and new submissions still go there. Do not edit these files before cutover: they will be regenerated from a fresh pull of the live data and edits would be overwritten.

One JSON file per dataset in `datasets/`, following `../schema/dataset.schema.json` (see `../schema/README.md` for the field reference and filename rule).

These files were generated from the legacy `lod-data.json` by `../scripts/migrate_lod_data.py`:

    python3 scripts/migrate_lod_data.py lod-data.json data --report report.md

The script is only needed once, to cut over from the old server; after that the files are edited directly. It also prints a report of what it normalised and what still violates the schema.

## `conflicts/`

Five legacy records have an identifier that differs from another only by case, which cannot coexist as files on macOS or Windows. The record with more links and resources was kept in `datasets/`, and the other was set aside here (file name: lower-cased identifier plus a hash). They are valid records and must be merged into the kept dataset, renamed, or deleted by a maintainer.

| Kept in `datasets/` | Set aside in `conflicts/` |
|---|---|
| `Test` | `test` |
| `WHOnto` | `whonto` |
| `abc` | `ABC` |
| `caligraph` | `CaLiGraph` |
| `uniprot` | `UniProt` |

`WHOnto`/`whonto` look like two different ontologies; `CaLiGraph` and `UniProt` look like duplicates; `test`, `Test`, `abc` and `ABC` look like test submissions.

## Known data problems

The migration only makes mechanical fixes, so many records do not yet satisfy the schema (missing domain, website, description or contact email, links to datasets that no longer exist, malformed URLs). The validation script (#90) will carry a known-issues list so that existing problems do not block every pull request while new and changed records are held to the schema.

## Validation

    pip install -r scripts/requirements.txt
    python3 scripts/validate.py                       # whole data set, known issues allowed
    python3 scripts/validate.py --changed-from main   # files changed since main must have no problems at all
    python3 scripts/validate.py --strict a.json b.json
    python3 -m unittest discover tests                # tests for the validator itself

`known-issues.json` lists, per file, the problems that existed when the data was migrated (2,646 across 1,067 files). They are tolerated so unrelated changes are not blocked, but any file you change must be fully valid, and any new problem anywhere fails. When you fix problems, regenerate the list with `python3 scripts/validate.py --write-known-issues` (it only ever needs to shrink; the run reports entries that no longer occur).

## Adding and changing datasets

Contributors who do not want to edit JSON use the issue forms (**Submit a dataset** on the site, or *New issue* here): *Add a dataset* and *Update a dataset*. The **Submissions** workflow (`.github/workflows/submissions.yml`, `scripts/issue_to_record.py`) turns the issue into a pull request against `dev` with the new or changed file in `data/datasets`, commits it with the submitter as co-author, and links the pull request in a comment on the issue. The Validate workflow then checks it like any other pull request, and a maintainer reviews and merges it (there is no auto-merge).

- If the form cannot be turned into a valid record, the workflow comments with the list of problems and opens nothing; editing the issue runs it again, and updates the pull request if there already is one.
- In an update a blank field means "unchanged", and a filled-in list (downloads, endpoints, keywords, links) replaces the current one. Removing a value is done by editing the file.
- The checks cover the whole record, as for any change to a file (see Validation), so updating a dataset that has a known problem needs the problem fixed in the same form.
- Only issues created from the two forms (they carry the `add-dataset` / `update-dataset` label) are processed. The issue text is only parsed, never run.

### Setting up the Submissions app (maintainers, once)

A pull request opened with the default `GITHUB_TOKEN` does not trigger the Validate check, which the branch rules require, so the workflow uses a GitHub App:

1. Organisation settings → Developer settings → GitHub Apps → New GitHub App. Name it e.g. `lod-cloud-submissions`; no webhook; permissions *Repository → Contents: read and write* and *Pull requests: read and write*; installable only on this account.
2. Generate a private key, and note the App ID.
3. Install the App on `lod-cloud/lod-cloud-site` only.
4. In the repository, Settings → Secrets and variables → Actions: add `SUBMISSIONS_APP_ID` (the App ID) and `SUBMISSIONS_APP_PRIVATE_KEY` (the whole `.pem` file).
5. Create the labels `add-dataset` and `update-dataset` (the forms apply them; creating them first just gives them a colour).

The workflow only runs once it is on `main`. Until the App exists, the workflow fails at the "create-github-app-token" step, after it has already commented on invalid submissions.

## Link status

Whether the download, example and SPARQL URLs still respond is checked weekly by the **Links** workflow (`scripts/check_links.py`). The result for each URL (`status`, `http`, `last_checked`, `last_ok`, `failures`: the number of failed checks in a row) is kept in `resources.json` on the `link-status` branch, not in the dataset files and not on `main` or `dev`. The results are informational: some servers block the addresses of GitHub's runners, so a single failure means little and `failures` is the number to look at.

To keep the number of requests to other people's servers down, each distinct URL is requested once (HEAD, or GET for examples), one request at a time per host; a URL that was OK is not checked again for 28 days; and a host that cannot be reached is given up after three connection errors. To try it: `python3 scripts/check_links.py --state /tmp/resources.json --limit 100`.

### Unavailable datasets

A dataset is never removed because its links stopped working, so the cloud does not shrink; it is flagged. `scripts/availability.py` reads the link status and marks a dataset **unavailable** when *every* one of its download, SPARQL and example URLs has been failing for 90 days (`failing_since` in the status file). A dataset with any working, non-web or not-yet-checked URL is never flagged, and nothing is flagged until it has been monitored for the full 90 days, so a blocked runner or a bad week does not mark a dataset. The dataset page then shows "Unavailable since DATE" and the domain pages a badge; every dataset page shows when its links were last verified (the latest `last_ok`).

After 365 days a dataset is an **archive candidate**. That is a prompt for a person, not an automatic step: the Links workflow lists the candidates in its run summary, and a maintainer decides, usually after trying the contact point, whether to remove the record by pull request (the history keeps it). The workflow also opens an issue for each one ("Archive candidate: <identifier>", label `archive-candidate`, at most 10 a run so a backlog is worked through over several weeks). An issue is never opened twice, closed ones included, so closing it means "keep". Contact details are not put in the issue. A flag clears by itself the first time one of the URLs responds again. The thresholds are `--unavailable-days` and `--archive-days`.

The diagrams still draw every dataset; dimming flagged ones would need a change in `lod-cloud-draw`.
