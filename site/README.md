# LOD Cloud site

A [Jekyll](https://jekyllrb.com/) site generated from the dataset files in `../data/datasets`. It replaces the Java application in `src/` and is not deployed yet (see #105).

## Build

With Ruby 3.3 and Bundler:

    cd site
    bundle install
    bundle exec jekyll serve      # http://localhost:4000

or without installing Ruby:

    docker run --rm -v "$PWD:/repo" -w /repo/site -e BUNDLE_PATH=/tmp/bundle ruby:3.3 \
        bash -c "bundle install && bundle exec jekyll build --destination /repo/_site"

Check the result with `python3 scripts/check_site_links.py _site`. CI (`.github/workflows/site.yml`) does the same and checks that every dataset has a page.

## Layout

| Path | |
|---|---|
| `_plugins/lodcloud.rb` | Reads `data/datasets/*.json`, creates `/dataset/<identifier>/` and `/domain/<domain>/` pages and the Liquid filters |
| `_layouts/` | `default` (page frame), `dataset`, `domain` |
| `_includes/versions-table.html` | History table on the home page (one row per published diagram) |
| `index.html`, `datasets/index.html` | Home page and the list of all datasets |
| `privacy.html`, `ipfs-how-to.html` | Static pages carried over unchanged |

Text from dataset files is escaped, and URLs are only emitted if they start with `http://`, `https://` or `ftp://` (`safe_url`), because records arrive through pull requests.

## Temporary settings in `_config.yml`

- `cloud_base`: the diagrams under `clouds/` and `versions/` are not generated here yet (#97, #98), so they load from the live site. Set it to `""` when the site serves its own.
- `github_branch`: edit and source links point at this branch of the repository.
- `submit_url`: where "Submit a dataset" goes until the issue forms exist (#92).
- `/lod-data.json` (linked from the home page) is not produced yet (#95).
