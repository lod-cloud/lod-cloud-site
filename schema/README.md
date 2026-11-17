# Dataset record schema

`dataset.schema.json` (JSON Schema 2020-12) defines one dataset in the LOD Cloud. It replaces the unused `validate_json` in `LODCloudServlet.java`. See `examples/valid.json` for a complete record.

Each dataset is one JSON file in `data/datasets/` (2-space indent, UTF-8, keys in the order below, `links` sorted by target).

## Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `identifier` | yes | string | Used in URLs. No whitespace, `/`, `\` or `?`. |
| `title` | yes | string | |
| `description` | yes | object | Language tag to text. `en` is required. |
| `domain` | yes | enum | `cross_domain`, `geography`, `government`, `life_sciences`, `linguistics`, `media`, `publications`, `social_networking`, `user_generated` |
| `website` | yes | http(s) URL | |
| `contact_point` | yes | object | `email` required, `name` optional |
| `license` | no | http(s) URL | |
| `triples` | no | integer | |
| `namespace` | no | http(s) URL | |
| `doi` | no | string | Bare DOI (`10.xxxx/...`) |
| `image` | no | http(s) URL | |
| `keywords` | no | string[] | |
| `links` | no | `{target, value?}[]` | Directed, stored on the source only. `value` is omitted when unknown. |
| `full_download` | no | resource[] | `download_url` required |
| `other_download`, `example`, `sparql` | no | resource[] | `access_url` required |

Optional fields and empty lists are omitted rather than written as `""`, `null` or `[]`. Consumers must treat absence as empty.

## Filename rule

The file for a dataset is `<identifier>.json` with every character outside `A-Za-z0-9_-` percent-encoded as UTF-8 bytes (uppercase hex). A `.` is kept only when it is neither the first nor the last character. This keeps filenames ASCII and valid on Windows and macOS (identifiers currently contain `:`, `#`, `'`, non-ASCII letters and leading `_`). The `identifier` field inside the file is the source of truth, not the filename.

Identifiers must be unique **ignoring case**, so a checkout on a case-insensitive filesystem does not collapse two datasets. Five pairs in the legacy data violate this (see `data/README.md`).

## Differences from the legacy `lod-data.json`

| Legacy | Here |
|---|---|
| `_id` (top level and inside links/resources), `time` | dropped (MongoDB / edit-history artefacts) |
| `owner` | dropped. It was the submitter's Google account (names and emails), not dataset metadata; git history now records who changed a file. |
| `status`, `mirror` on resources | dropped. Link-check results are not part of the editable record; see the link checking issue (#99). |
| `Image` / `image` | `image` |
| `cross-domain` / `cross_domain` | `cross_domain` (the value `lod-cloud-draw` expects) |
| `domain: ""`, `website: null`, `license` missing, `doi: ""` etc. | field omitted |
| `triples` as string (`"1,008,772"`) | integer |
| link `value` as string (`"12"`) | integer, omitted if not a number |
| `description: {"en": ""}` | `description` omitted |

The old validator also rejected titles containing a space. That rule is not carried over: most real titles contain spaces.

## What the schema cannot check

These belong to the validation script (#90):

- `identifier` unique ignoring case, and the filename matches the identifier (rule above)
- every `links[].target` is an existing dataset; no duplicate targets; no self-links
- URL liveness (#99)

## Decisions for maintainers

Defaults were chosen to match the previous validator where it had a rule. Change `dataset.schema.json` if you disagree.

1. **Required fields**: `identifier`, `title`, `description.en`, `domain`, `website`, `contact_point.email`. Legacy records that lack these will fail until fixed or grandfathered (#90).
2. **Contact emails are public**: they are published with each dataset, as they are on the current site. Consider whether a contact email should be required for a public repository (GDPR applies to the University of Galway).
3. **No minimum resources**: a record with no download, example or SPARQL endpoint is valid. Add a rule if the cloud requires at least one.
4. **License is a free http(s) URL**, not an enum, because legacy values mix several URL styles.
