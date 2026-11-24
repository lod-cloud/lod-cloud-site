# The Linked Open Data Cloud

Source of [lod-cloud.net](https://lod-cloud.net/): the catalogue of Linked Open Data datasets and the LOD Cloud diagram.

The site is static. The catalogue is one JSON file per dataset in [`data/datasets/`](data/datasets), the pages, exports and search index are built from those files with [Jekyll](https://jekyllrb.com/) in GitHub Actions, and the diagrams are drawn by a monthly Action with [`lod-cloud-draw`](https://github.com/lod-cloud/lod-cloud-draw). Nothing runs on a server except a reverse proxy in front of GitHub Pages.

## Add or change a dataset

- **Without editing JSON:** use the *Add a dataset* or *Update a dataset* form (**Submit a dataset** on the site, or *New issue* here). A pull request is opened for you and checked automatically.
- **By pull request:** edit or add a file in `data/datasets/`.

Both are explained, with what the checks mean and what happens to datasets whose links stop working, in **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Repository

| Path | What it is |
|---|---|
| `data/datasets/` | The catalogue: one JSON file per dataset ([`schema/`](schema) describes the fields) |
| `data/known-issues.json` | Problems in old records that are tolerated until the record is next changed |
| `site/` | The Jekyll site (layouts, the plugin that builds the dataset pages, the home page) |
| `scripts/` | Validation, export of the static data files, link checking, diagram generation, the issue-form converter |
| `tests/` | Unit tests for the scripts (`python3 -m unittest discover tests`) |
| `cloud-settings/` | Settings for the diagram of each domain |
| `.github/workflows/` | Validate, Site (build and publish), Links, Clouds, Submissions |
| `.github/ISSUE_TEMPLATE/` | The add and update forms |
| `src/`, `pom.xml`, `Dockerfile` | The old Java application, kept until it is removed (#105); not used any more |

## Working on it locally

You need Python 3.12 and, to build the site, Ruby 3.3 (or Docker).

    pip install -r scripts/requirements.txt
    python3 scripts/validate.py                  # the dataset files
    python3 -m unittest discover tests           # the scripts

The site build and the checks are described in [`site/README.md`](site/README.md). The data files and their known problems are in [`data/README.md`](data/README.md), and maintenance (the workflows, secrets, hosting) in **[MAINTAINING.md](MAINTAINING.md)**.

## The diagram

The diagrams are drawn from the same data by the *Clouds* workflow and published as [releases](https://github.com/lod-cloud/lod-cloud-site/releases) (one per version, back to 2007). You may reuse them under the Creative Commons Attribution License; see the [site](https://lod-cloud.net/#about) for the attribution to give.

## Contact

The LOD Cloud is maintained by [John P. McCrae](http://john.mccr.ae/) for the Insight Centre for Data Analytics, University of Galway. Questions and problems: [open an issue](https://github.com/lod-cloud/lod-cloud-site/issues).
