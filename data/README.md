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
