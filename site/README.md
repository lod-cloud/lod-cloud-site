# LOD Cloud site

A [Jekyll](https://jekyllrb.com/) site generated from the dataset files in `../data/datasets`. It replaces the Java application in `src/` and is not deployed yet (see #105).

## Build

With Ruby 3.3, Bundler and Python 3 (`pip install -r scripts/requirements.txt`):

    cd site
    bundle install
    bundle exec jekyll build --destination ../_site
    cd ..
    python3 scripts/export_site_data.py _site     # json/, rdf/, ttl/, nt/, lod-data.json ... (see below)

`bundle exec jekyll serve` previews the pages, but not the exported files. Without Ruby, the Jekyll step runs in a container:

    docker run --rm -v "$PWD:/repo" -w /repo/site -e BUNDLE_PATH=/tmp/bundle ruby:3.3 \
        bash -c "bundle install && bundle exec jekyll build --destination /repo/_site"

Check the result with `python3 scripts/check_site_paths.py _site` and `python3 scripts/check_site_links.py _site`. CI (`.github/workflows/site.yml`) runs all of this.

## Layout

| Path | |
|---|---|
| `_plugins/lodcloud.rb` | Reads `data/datasets/*.json`, creates `/dataset/<identifier>/` and `/domain/<domain>/` pages and the Liquid filters |
| `_layouts/` | `default` (page frame), `dataset`, `domain` |
| `_data/versions.yml`, `_includes/versions-table.html` | History table on the home page: one entry per published diagram in the data file, rendered as rows (see the comments at the top of the file for the fields) |
| `index.html`, `datasets/index.html` | Home page and the list of all datasets |
| `privacy.html`, `ipfs-how-to.html` | Static pages carried over unchanged |
| `404.html` | Not-found page; also sends old URLs of identifiers with an encoded path to the right place (below) |

Text from dataset files is escaped, and URLs are only emitted if they start with `http://`, `https://` or `ftp://` (`safe_url`), because records arrive through pull requests.

## Temporary settings in `_config.yml`

- `cloud_base`: the diagrams under `clouds/` and `versions/` are not generated here yet (#97, #98), so they load from the live site. Set it to `""` when the site serves its own.
- `github_branch`: edit and source links point at this branch of the repository.
- `submit_url`: where "Submit a dataset" goes until the issue forms exist (#92).

## Old URLs

The Java application served these routes. Static hosting cannot do everything they did.

| Old route | Now |
|---|---|
| `/dataset/<id>` | `/dataset/<id>/` (HTML). **No content negotiation**: a request with `Accept: text/turtle` etc. used to be redirected to the RDF, and now gets the HTML page. Each page advertises the other formats with `<link rel="alternate">` in its `<head>` (and links to them), which is the only discovery mechanism available. |
| `/json/<id>`, `/api/<id>` (GET) | Same paths, the dataset in the old JSON format. |
| `/rdf/<id>?format=ttl\|rdf\|nt` | `/rdf/<id>` (RDF/XML), `/ttl/<id>` (Turtle), `/nt/<id>` (N-Triples). A static server ignores `?format=`, so an old link to `/rdf/<id>` now returns **RDF/XML whatever the query says**: `?format=rdf` links are right; bare `/rdf/<id>` and `?format=ttl` (the old default) now return RDF/XML, not Turtle, and `?format=nt` links likewise. Use `/ttl/<id>` and `/nt/<id>`. |
| `/extract/datasets` | Same path, and `/lod-data.json` (identical content), in the old format. |
| `/extract/rdf` | Same path, all datasets as N-Triples. |
| `/datasets` | `/datasets/` |
| `/edit-dataset/<id>` | Redirects to the dataset's file on GitHub (edit page). |
| `/add-dataset` | Redirects to `submit_url` (#92). |
| `/clouds/...`, `/versions/...` | Diagram files; produced by #97 and #98. |
| `/privacy.html`, `/ipfs-how-to.html` | Unchanged. |
| `PUT`, `POST`, `DELETE /api/<id>` | **Removed.** Datasets change by pull request. |
| `/extract/history` | **Removed.** It was the in-memory edit log; git history replaces it. |
| `/datasets_search` | **Removed**; search is #96. |
| `/authorize`, `/oauth2callback`, `/logout` | **Removed** (Google login). |
| `/update-clouds` | **Removed**; diagrams are built by an Action (#97). |
| `/ilod/*` | **Removed.** It redirected to `server1.nlp.insight-centre.org/ilod`, an external service this repository has no information about. |

`/json/` and `/api/` have no file extension, as before; the server decides the content type, so a browser may download rather than display them.

### The old JSON format

`lod-data.json` and `json/<id>` keep the old shape so existing consumers (`GetData`, `lod-cloud-draw`) still work: every list is present even if empty, link counts are strings (`"unknown"` when there is no count), and a missing `website` is `null`. Fields the migration dropped (`owner`, `status`, `mirror`) are not restored.

### The RDF

`rdf/<id>`, `ttl/<id>`, `nt/<id>` and `extract/rdf` are a port of `RDFView.java`, with the same VoID/DCAT/DCTerms/FOAF terms and dataset URIs (`http://lod-cloud.net/dataset/<id>`). Differences: the license is now emitted (the Java code read a field that never existed), IRIs with spaces and similar are percent-encoded instead of producing invalid N-Triples, and link targets are encoded the same way as dataset URIs. The model itself is unchanged; moving to DCAT-3 is #101.

### Identifiers that cannot be file names

28 identifiers contain a character that GitHub's artifact upload and Windows reject in a path (`" < > : | * ? \`, e.g. `ISSN:0080-3626`). Their pages and files are written under the percent-encoded name (`dataset/ISSN%3A0080-3626/`), and `404.html` sends a browser that asks for `/dataset/ISSN:0080-3626` or `/edit-dataset/...` there, using `dataset-redirects.json`. The rule exists twice (`LODCloud.dataset_path` in the plugin and `dataset_path` in `scripts/export_site_data.py`); `scripts/check_site_paths.py` fails the build if they disagree. This has not been tested on GitHub Pages itself (#105).
