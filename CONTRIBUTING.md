# Contributing to the LOD Cloud

Thank you for helping to keep the LOD Cloud up to date. This page explains how to add or change a dataset, what the automatic checks mean, what happens to datasets whose links stop working, how the diagram is made, and how pull requests are reviewed.

## Does the dataset belong in the cloud?

The criteria are those on the [home page](https://lod-cloud.net/#about):

- There are resolvable `http://` (or `https://`) URIs.
- They resolve, with or without content negotiation, to RDF in a popular format (RDFa, RDF/XML, Turtle, N-Triples).
- The dataset contains at least 1,000 triples.
- It is connected by RDF links to a dataset that is already in the diagram: it uses URIs from the other dataset, or the other way round, with at least 50 links.
- The whole dataset can be accessed by crawling, from an RDF dump, or through a SPARQL endpoint.

## Adding or updating a dataset

### With a form (no JSON needed)

1. Open **Submit a dataset** on the site (or *New issue* in this repository) and choose *Add a dataset* or *Update a dataset*. You need a GitHub account.
2. Fill in the form. For a new dataset the identifier, title, description, domain, website and a contact email are required; everything else helps. Lists (downloads, SPARQL endpoints, examples, links) go one per line: `URL` or `URL | title`, and for links `identifier | number of links`.
3. **The contact email is published** with the dataset, on a public site. Use a role address if you prefer.
4. Submit. Within a minute a bot comments on your issue with the link to a pull request, or with a list of what needs fixing. If something is wrong, edit the issue and save: the check runs again and an existing pull request is updated.
5. A maintainer reviews the pull request and merges it. The site is updated a few minutes after that.

To update a dataset, use *Suggest a change (form)* at the bottom of its page: the identifier is filled in. Leave a field blank to keep its current value. A list you fill in replaces the current list. To *remove* a value, edit the file (below).

### With a pull request

1. Find or create the file `data/datasets/<identifier>.json` (the *Edit* link on a dataset page opens it). The fields are in [`schema/README.md`](schema/README.md), including the rule for the file name when an identifier has characters other than letters, digits, `-`, `_` and `.`.
2. Keep to the existing style: two-space indent, keys in the order of the schema, optional fields left out rather than empty.
3. Check it:

        pip install -r scripts/requirements.txt
        python3 scripts/validate.py --strict data/datasets/<file>.json

4. Open a pull request against `main`. The **Validate** check runs on it; it has to pass before the pull request can be merged.

## What the checks mean

**Validate** (`scripts/validate.py`) checks the files you change with no allowances. Problems it reports:

| Message | Meaning and fix |
|---|---|
| `schema: ... is a required property` | A required field is missing: `identifier`, `title`, `description` (with an English `en` entry), `domain`, `website`, `contact_point` (with an `email`). |
| `schema: '...' does not match '^https?://\S+$'` | A URL field (`website`, `license`, `namespace`, `image`, a download or access URL) is not a full URL starting with `http://` or `https://` (downloads may also be `ftp://`). |
| `schema: ... is not one of [...]` | `domain` is not one of the nine cloud domains. |
| `schema: ... is not of type 'integer'` | `triples` and link `value` are whole numbers. |
| `filename: file name does not match identifier` | The file is not named by the rule in `schema/README.md`. |
| `duplicate-identifier` | Another dataset has the same identifier ignoring case (so the two files could not exist side by side on macOS or Windows). |
| `link-target-missing` | `links` names a dataset that is not in the catalogue. Fix the identifier, or remove the link. |
| `link-self`, `link-duplicate-target` | A dataset links to itself, or to the same dataset twice. |
| `json` / `stray-file` | The file is not valid JSON, or something other than a `.json` file is in `data/datasets/`. |

**Old records.** Many records that came from the old server already break these rules (about 2,600 problems in 1,068 files). They are listed in [`data/known-issues.json`](data/known-issues.json) and do not block unrelated pull requests. But **a record you change has to be fully valid**, including the old problems in it, so changing a dataset may include fixing a missing website or a dead link target in the same change. If you are not sure how, say so in the pull request and a maintainer will help. Fixed problems can be removed from the list with `python3 scripts/validate.py --write-known-issues`.

**Site** builds the whole site from the data and checks that every dataset has its pages and files and that no internal link is broken.

## Datasets whose links stop working

A weekly workflow (**Links**) requests every download, SPARQL and example URL once, and keeps the result per URL on the `link-status` branch (`status`, `last_ok`, `failures`, `failing_since`). A URL that worked is not asked again for 28 days, and no more than one request at a time goes to any host.

Datasets are **not removed** for having dead links, so the cloud does not seem to shrink:

- When *every* URL of a dataset has been failing for **90 days**, its page shows *Unavailable since DATE* and a badge in the domain lists. One working link, or one URL that is not a web address or not yet checked, is enough for it not to be flagged. Every dataset page shows when its links were last verified.
- After **365 days** it is an **archive candidate**: the workflow opens an issue `Archive candidate: <identifier>` (at most ten new ones per run). A maintainer then decides: update the links if the dataset has moved, remove the file in a pull request (history keeps it), or close the issue to keep the record, in which case it is not opened again.
- If the dataset has moved, or you know where, [update it](#adding-or-updating-a-dataset). The flag disappears when one of its URLs responds again.

Servers sometimes block the addresses of GitHub's runners, so one failure means little; the 90 days are there for that reason.

## How the diagram is made

The **Clouds** workflow draws the diagram on the first of each month, or when a maintainer runs it. It exports the dataset files in the format of the old `lod-data.json`, runs the [`lod-cloud-draw`](https://github.com/lod-cloud/lod-cloud-draw) release named in the workflow (checksum checked) for the whole cloud and each of the nine domains, converts the SVGs to PNG, publishes the 32 files as the GitHub release `clouds-<date>`, and opens a pull request that adds the version to the history table. The settings of each diagram are in `cloud-settings/`. Not every dataset in the catalogue is drawn (1,368 of 1,690 on 2026-11-23); the history table shows how many each version has. To change how the diagram looks or is laid out, change `lod-cloud-draw` or `cloud-settings/`.

## Review and merge (maintainers)

- Every pull request is reviewed by a maintainer; there is no auto-merge, also for the pull requests the form creates.
- **Validate** must pass. Administrators can bypass the rule; do so only for bulk imports of data and say why in the pull request.
- For a new dataset, check the criteria above (does the dataset resolve and have an RDF dump or SPARQL endpoint?), that the description and website are about the dataset, and that it is not a duplicate of one that exists. Submissions that are spam or test records are closed.
- Merge with a merge commit or squash, as suits. After merging to `main`, the **Site** workflow publishes the site (see [MAINTAINING.md](MAINTAINING.md)). The monthly diagram pull request needs *Approve workflows to run* once before its checks run.
- Questions about a submission go in the pull request. Do not put people's email addresses in comments.
