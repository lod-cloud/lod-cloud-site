# LOD Cloud site

A [Jekyll](https://jekyllrb.com/) site generated from the dataset files in `../data/datasets`. It replaces the Java application in `src/` (see #105 for the move; "Publishing" below).

## Build

With Ruby 3.3, Bundler and Python 3 (`pip install -r scripts/requirements.txt`):

    cd site
    bundle install
    bundle exec jekyll build --destination ../_site
    cd ..
    python3 scripts/export_site_data.py _site     # json/, rdf/, ttl/, nt/, lod-data.json ... (see below)
    npx pagefind@1.4.0 --site _site               # the search index, _site/pagefind/ (needs Node)

`bundle exec jekyll serve` previews the pages, but not the exported files. Without Ruby, the Jekyll step runs in a container:

    docker run --rm -v "$PWD:/repo" -w /repo/site -e BUNDLE_PATH=/tmp/bundle ruby:3.3 \
        bash -c "bundle install && bundle exec jekyll build --destination /repo/_site"

The search page (`/search/`) uses [Pagefind](https://pagefind.app), which indexes the built pages in the last step above, in the browser, with no server. Only the dataset pages are indexed (`data-pagefind-body` in `_layouts/dataset.html`): title, identifier, description and keywords, with the domain and availability as filters. Without the index step the search page says so. With Node, `npx pagefind --site _site --serve` serves the result.

Check the result with `python3 scripts/check_site_paths.py _site` and `python3 scripts/check_site_links.py _site`. CI (`.github/workflows/site.yml`) runs all of this.

## Layout

| Path | |
|---|---|
| `_plugins/lodcloud.rb` | Reads `data/datasets/*.json`, creates `/dataset/<identifier>/` and `/domain/<domain>/` pages and the Liquid filters |
| `_layouts/` | `default` (page frame), `dataset`, `domain` |
| `_data/versions.yml`, `_includes/versions-table.html` | History table on the home page: one entry per published diagram in the data file, rendered as rows (see the comments at the top of the file for the fields) |
| `index.html`, `datasets/index.html` | Home page and the list of all datasets |
| `cloud/index.html`, `cloud/datasets.json`, `assets/cloud.js` | The interactive diagram (below) |
| `privacy.html`, `ipfs-how-to.html` | Static pages carried over unchanged |
| `404.html` | Not-found page; also sends old URLs of identifiers with an encoded path to the right place (below) |

Text from dataset files is escaped, and URLs are only emitted if they start with `http://`, `https://` or `ftp://` (`safe_url`), because records arrive through pull requests.

## Settings in `_config.yml`

- `cloud_base`: where the diagrams under `/clouds/` come from; `""`, because the build downloads the current set from its release into the site (below). A preview under a path sets it, with `baseurl`, to that path.
- `github_branch`: edit and source links point at this branch of the repository.
- `submit_url`: where "Submit a dataset" goes (the issue forms, #92).

## Publishing

`.github/workflows/site.yml` builds and checks the site on every pull request and push. A push to `main` also publishes the checked site to GitHub Pages (Settings → Pages → Source: *GitHub Actions*), at `https://lod-cloud.github.io/lod-cloud-site/`. `lod-cloud.net` is served from there by a reverse proxy that maps `/` to that address (#105), so the site is built for the root of its host (`baseurl: ""`).

- **Preview.** While the site is only reachable at the Pages address, the repository variable `PAGES_BASEURL` is `/lod-cloud-site`: the build then prefixes every link with it and the pages say `noindex`. Setting it to empty (or deleting it) at the cutover makes the next push to `main` build for the root.
- **Diagrams.** `scripts/fetch_clouds.py` downloads the files of the newest release listed in `_data/versions.yml` into `_site/clouds/`, because release downloads are attachments and cannot be shown in a page or used as an interactive SVG. Since #117 the diagrams are published as **lossless WebP** (half the size of the PNG, the same pixels) and the pages show those; the build makes the **PNG** of each diagram from its WebP (or the WebP from the PNG, for a release made before) so that `/clouds/lod-cloud.png` and the other old addresses, which many pages link to, still work. The PNGs are in the site, not in the releases. In the history table a set made since #117 shows `webp` where older ones show `png`. `/versions/<dir>/` pages redirect to the release of that set; the old file URLs below them (`/versions/<dir>/lod-cloud.png`) are not redirected, because static hosting has no way to.
- **Canonical address.** Every page has `<link rel="canonical">` to `https://lod-cloud.net/...` so the Pages address is not a competing copy.

## Diagrams

The diagrams are drawn by the **Clouds** workflow (`.github/workflows/clouds.yml`), monthly or on demand
(`gh workflow run clouds.yml`, optionally `-f date=yyyy-mm-dd -f iterations=500` for a quick test). It
exports the dataset files in the old `lod-data.json` format, runs `scripts/generate_clouds.py` with the
pinned `lod-cloud-draw` release (checksum verified), publishes the 32 files as the GitHub release
`clouds-<date>`, and opens a pull request adding the entry (with `release: clouds-<date>`) to
`_data/versions.yml`. The settings for each diagram are in `cloud-settings/`.

To draw locally: `python3 scripts/generate_clouds.py --binary path/to/lod-cloud-draw --data lod-data.json --out out`
(needs `rsvg-convert` and ImageMagick; `lod-data.json` comes from `scripts/export_site_data.py`).

Releases keep the repository small (#98). They are served as downloads (`Content-Disposition: attachment`),
so the history table links to them but the page cannot show them; the current diagram on the home page has to
be served from Pages (to do at cutover, #105). The 45 sets from the old site are uploaded to releases once, by
a local script that is not part of the repository; entries in `versions.yml` without `release:` still link to
`versions/` on `cloud_base`.

### The interactive diagram

`/cloud/` (#107; the home page and the domain pages link their images to it) shows the current
`clouds/lod-cloud.svg`, or with `?domain=<key>` that domain's subcloud, inside the page: zoom (wheel, pinch,
`+`/`−`, `0` to fit), pan (drag, arrow keys), a filter by domain (double-click a domain to show only it), an
option to hide unavailable datasets, and a search. Clicking a dataset highlights its links and opens a panel
listing the datasets it links to and those linking to it; `?d=<identifier>` opens with a dataset selected, and
the address follows the selection so it can be shared. Ctrl- or Cmd-click opens the dataset page as before.

It uses the SVG that `lod-cloud-draw` writes, with nothing added to the generator: each dataset is a `<g>`
with a `<circle>` (its `<title>` is the identifier) and an `<a>`; each link is a `<line>` whose `targetId`
is the dataset whose record has the link and `sourceId` the dataset it links to. The SVG's own script and
style are removed and the page's replace them. Titles, page URLs and availability come from
`cloud/datasets.json`, built with the site. A dataset's domain in the filter is the colour it is drawn in,
because `lod-cloud-draw` colours the records that have no `domain` as well (218 in November 2026). The
datasets drawn are those in the diagram, which is regenerated monthly, so a dataset added since is not in it.

## Old URLs

The Java application served these routes. Static hosting cannot do everything they did.

| Old route | Now |
|---|---|
| `/dataset/<id>` | `/dataset/<id>/` (HTML). **No content negotiation**: a request with `Accept: text/turtle` etc. used to be redirected to the RDF, and now gets the HTML page. Each page advertises the other formats with `<link rel="alternate">` in its `<head>` (and links to them), and **carries the dataset's RDF as JSON-LD** in a `<script type="application/ld+json" id="dataset-jsonld">` in the head, so a client that fetches the page can read the RDF from it. |
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
| `/datasets_search` | **Replaced** by `/search/` (Pagefind, see below). It matched the identifier only; the new search covers title, identifier, description and keywords. |
| `/authorize`, `/oauth2callback`, `/logout` | **Removed** (Google login). |
| `/update-clouds` | **Removed**; diagrams are built by an Action (#97). |
| `/ilod/*` | **Removed.** It redirected to `server1.nlp.insight-centre.org/ilod`, an external service this repository has no information about. |

`/json/` and `/api/` have no file extension, as before; the server decides the content type, so a browser may download rather than display them.

### The old JSON format

`lod-data.json` and `json/<id>` keep the old shape so existing consumers (`GetData`, `lod-cloud-draw`) still work: every list is present even if empty, link counts are strings (`"unknown"` when there is no count), and a missing `website` is `null`. Fields the migration dropped (`owner`, `status`, `mirror`) are not restored.

### The RDF

`rdf/<id>`, `ttl/<id>`, `nt/<id>` and `extract/rdf` are a port of `RDFView.java` (VoID, DCTerms, FOAF; dataset URIs `http://lod-cloud.net/dataset/<id>`), with **DCAT-3 added**. Every statement of the old files is still there, so consumers of the old RDF are not affected (checked against the old site's `extract/rdf`: no statement missing); the files are larger (`extract/rdf` 10.7 → 26 MB).

Each dataset is a `void:Dataset` and a `dcat:Dataset`:

| Data | RDF |
|---|---|
| identifier, DOI | `dcterms:identifier` (the DOI as `https://doi.org/...`) |
| title, description (per language) | `dcterms:title`, `dcterms:description` |
| website | `foaf:homepage` and `dcat:landingPage` |
| domain | `dcterms:subject` (the key) and `dcat:theme` (a `skos:Concept`, `http://lod-cloud.net/domain/<key>/`) |
| keywords | `dcterms:subject` and `dcat:keyword` |
| contact | `dcterms:publisher` (as before) and `dcat:contactPoint` (a `vcard:Kind`) |
| license, namespace, image | `dcterms:license`, `void:uriSpace`, `foaf:depiction` |
| triples | `void:triples` |
| full downloads | `void:dataDump`, and a `dcat:Distribution` with `dcat:downloadURL` (also `dcat:accessURL`, `dcterms:title`, `dcat:mediaType` as an IANA URI when the media type is one) |
| other downloads | a `dcat:Distribution` with `dcat:accessURL` |
| SPARQL endpoints | `void:sparqlEndpoint`, and a `dcat:Distribution` whose `dcat:accessService` is a `dcat:DataService` (`dcat:endpointURL`, `dcat:servesDataset`, `dcterms:conformsTo` the SPARQL protocol) |
| examples | `void:exampleResource` |
| each link | a `void:Linkset` named `<dataset>#linkset-<target>` with `void:subjectsTarget` (the dataset), `void:objectsTarget` (the target), `void:target` (both, as before) and `void:triples` when the count is known |

**In the dataset pages.** Each dataset page has the same RDF as JSON-LD (the graph of `rdf/<id>`, with the namespace prefixes as the `@context`; the page grows by 4 to 10 KB) in its head, written by `scripts/export_site_data.py` into the page Jekyll built. The dataset URI (`http://lod-cloud.net/dataset/<id>`) is the subject, so the page and the dataset it describes share a URI; this does not meet the W3C 303 recommendation but is the best a static host allows. Text from the data is escaped (`<`, `>`, `&` as `\uXXXX`) so a record cannot end the script. `scripts/check_site_paths.py` fails if a page lacks it or describes another dataset. It is DCAT/VoID, not schema.org, so search engines' dataset search will not read it.

`catalog.ttl` and `catalog.jsonld` hold the whole catalogue: a `dcat:Catalog` (`http://lod-cloud.net/#catalog`) with `dcat:dataset` for each dataset, the nine domains as a `skos:ConceptScheme` (`dcat:themeTaxonomy`), and all the datasets as above.

Differences from the Java output: the license is emitted (the Java code read a field that never existed), IRIs with spaces and similar are percent-encoded instead of producing invalid N-Triples, link targets are encoded like dataset URIs, and links without a known count are linksets too (the old files left them out).

**ShowVoc / MDR.** The [MDR ontology](https://w3id.org/mdr) extends DCAT, but its documentation defines no profile or example for describing a dataset, so nothing MDR-specific (`mdr:` classes) is emitted, and whether ShowVoc can ingest this as it is has not been tested (#103).

### SPARQL in the browser

`/sparql/` (prototype, linked from the home page) loads `catalog.ttl` into [Oxigraph](https://github.com/oxigraph/oxigraph) compiled to WebAssembly (`oxigraph@0.5.13` from jsDelivr, 4 MB) and runs SPARQL queries on it in the browser; nothing goes to a server. Seven examples (datasets per domain, most linked-to datasets, endpoints, links from DBpedia, a title search, large datasets, a CONSTRUCT); `?q=<query>&run=1` opens and runs a query; results are shown as text, never as HTML.

Measured on the real catalogue (197,347 triples, 10.7 MB): Oxigraph loads it in 0.4 s (+109 MB of memory) and answers each example in 1 to 30 ms. Comunica with N3 (the other candidate) takes 0.8 s and +193 MB, queries 20 to 430 ms, and it needs a bundling step for the browser (its dependencies are 21 MB unpacked; I did not measure a browser bundle). Both were measured in Node, not in a browser; only Oxigraph was tried in a browser (Chromium via Playwright). The cost is the download: Pages sends `catalog.ttl` uncompressed (10.7 MB; 0.9 MB gzipped), so the reverse proxy should compress `text/turtle` (and `application/ld+json`, `application/n-triples`).

The export refuses to publish an IRI that a strict RDF parser (Oxigraph, RDF4J, Jena) would reject: `[` and `]` are percent-encoded outside an IPv6 host, and a contact email that is not an address (one record has `a [at] b [dot] c`) gets no `vcard:hasEmail`.

### Identifiers that cannot be file names

28 identifiers contain a character that GitHub's artifact upload and Windows reject in a path (`" < > : | * ? \`, e.g. `ISSN:0080-3626`). Their pages and files are written under the percent-encoded name (`dataset/ISSN%3A0080-3626/`), and `404.html` sends a browser that asks for `/dataset/ISSN:0080-3626` or `/edit-dataset/...` there, using `dataset-redirects.json`. The rule exists twice (`LODCloud.dataset_path` in the plugin and `dataset_path` in `scripts/export_site_data.py`); `scripts/check_site_paths.py` fails the build if they disagree. This has not been tested on GitHub Pages itself (#105).
