# frozen_string_literal: true

require "erb"
require "json"

# Builds the site from the per-dataset JSON files in data/datasets
# (schema/dataset.schema.json): one page per dataset, one page per domain, and
# the data and Liquid filters the layouts use.
module LODCloud
  # domain => [label, stem of the diagram files]
  DOMAINS = {
    "cross_domain" => ["Cross-Domain", "cross-domain-lod"],
    "geography" => ["Geography", "geography-lod"],
    "government" => ["Government", "government-lod"],
    "life_sciences" => ["Life Sciences", "life-sciences-lod"],
    "linguistics" => ["Linguistics", "linguistic-lod"],
    "media" => ["Media", "media-lod"],
    "publications" => ["Publications", "publications-lod"],
    "social_networking" => ["Social Networking", "social-networking-lod"],
    "user_generated" => ["User-Generated", "user-generated-lod"]
  }.freeze

  # Same rule as scripts/validate.py (documented in schema/README.md).
  def self.filename(identifier)
    last = identifier.length - 1
    name = identifier.each_char.with_index.map do |ch, i|
      if ch.match?(/\A[A-Za-z0-9_-]\z/) || (ch == "." && i.positive? && i < last)
        ch
      else
        ch.bytes.map { |b| format("%%%02X", b) }.join
      end
    end.join
    "#{name}.json"
  end

  # Characters GitHub's upload-artifact refuses in a path (and NTFS forbids).
  # Keep in sync with UNSAFE in scripts/export_site_data.py;
  # scripts/check_site_paths.py checks the two agree on the built site.
  UNSAFE = /["<>:|*?\\\r\n]/.freeze

  # Directory / file name under dataset/, json/, rdf/, ttl/, nt/ ... for an identifier.
  # Identifiers with an unsafe character are percent-encoded; 404.html
  # redirects requests for the original spelling.
  def self.dataset_path(identifier)
    identifier.match?(UNSAFE) ? ERB::Util.url_encode(identifier) : identifier
  end

  # The same, as it appears in a URL.
  def self.url_path(identifier)
    ERB::Util.url_encode(dataset_path(identifier))
  end

  # Jekyll's URL handling rewrites some identifiers (e.g. one ending in "."),
  # so these pages are placed explicitly: <dir>/<dataset path>/index.html.
  class PlacedPage < Jekyll::PageWithoutAFile
    def initialize(site, dir, identifier)
      @identifier = identifier
      raise "Invalid dataset identifier #{identifier.inspect}" if [".", ".."].include?(identifier)

      @placed_dir = dir
      super(site, site.source, File.join(dir, LODCloud.dataset_path(identifier)), "index.html")
      @content = ""
      @data = {}
    end

    def url
      "/#{@placed_dir}/#{LODCloud.url_path(@identifier)}/"
    end

    def destination(dest)
      File.join(dest, @placed_dir, LODCloud.dataset_path(@identifier), "index.html")
    end
  end

  # An old URL that now goes somewhere else (static hosting has no redirects).
  class RedirectPage < PlacedPage
    def initialize(site, dir, identifier, target)
      super(site, dir, identifier)
      href = ERB::Util.html_escape(target)
      @content = <<~HTML
        <!DOCTYPE html>
        <html lang="en"><head><meta charset="utf-8"><title>Redirecting</title>
        <meta name="robots" content="noindex">
        <link rel="canonical" href="#{href}">
        <meta http-equiv="refresh" content="0; url=#{href}">
        </head><body><p>Moved to <a href="#{href}">#{href}</a>.</p></body></html>
      HTML
    end
  end

  class DatasetPage < PlacedPage
    ALTERNATES = [["application/json", "json"], ["application/rdf+xml", "rdf"],
                  ["text/turtle", "ttl"], ["application/n-triples", "nt"]].freeze

    def initialize(site, record)
      super(site, "dataset", record["identifier"])
      # Static hosting cannot negotiate content, so advertise the other formats.
      links = ALTERNATES.map do |type, dir|
        href = "#{site.baseurl}/#{dir}/#{LODCloud.url_path(record['identifier'])}"
        %(<link rel="alternate" type="#{type}" href="#{ERB::Util.html_escape(href)}">)
      end
      @data = { "layout" => "dataset", "title" => record["title"], "dataset" => record,
                "extra_head" => links.join("\n    ") }
    end
  end

  class DomainPage < Jekyll::PageWithoutAFile
    def initialize(site, domain, label, stem, records)
      super(site, site.source, File.join("domain", domain), "index.html")
      @content = ""
      @data = { "layout" => "domain", "title" => label, "domain" => domain,
                "label" => label, "stem" => stem, "datasets" => records }
    end
  end

  class Generator < Jekyll::Generator
    safe true
    priority :high

    def generate(site)
      dir = File.expand_path(site.config.fetch("dataset_dir"), site.source)
      files = Dir.children(dir).select { |f| f.end_with?(".json") }.sort
      raise "No dataset files found in #{dir}" if files.empty?

      records = files.map { |f| JSON.parse(File.read(File.join(dir, f), encoding: "utf-8")) }
      records.sort_by! { |r| [r["title"].to_s.downcase, r["identifier"]] }

      site.data["datasets"] = records
      site.data["dataset_index"] = records.to_h { |r| [r["identifier"], true] }
      site.data["domains"] = DOMAINS.map do |key, (label, stem)|
        { "key" => key, "label" => label, "stem" => stem,
          "count" => records.count { |r| r["domain"] == key } }
      end

      edit_base = "#{site.config.fetch('github_url')}/edit/#{site.config.fetch('github_branch')}/data/datasets/"
      records.each do |r|
        site.pages << DatasetPage.new(site, r)
        site.pages << RedirectPage.new(site, "edit-dataset", r["identifier"],
                                       edit_base + ERB::Util.url_encode(LODCloud.filename(r["identifier"])))
      end
      # /versions/<dir>/ held a diagram set; it is a release now (static hosting cannot redirect
      # the individual files, so only the directory page goes to the release).
      Array(site.data["versions"]).each do |v|
        next unless v["release"]

        site.pages << RedirectPage.new(site, "versions", (v["dir"] || v["date"]).to_s,
                                       "#{site.config.fetch('github_url')}/releases/tag/#{ERB::Util.url_encode(v['release'])}")
      end
      site.pages << Jekyll::PageWithoutAFile.new(site, site.source, "add-dataset", "index.html").tap do |p|
        href = ERB::Util.html_escape(site.config.fetch("submit_url"))
        p.content = %(<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Redirecting</title>) +
                    %(<link rel="canonical" href="#{href}"><meta http-equiv="refresh" content="0; url=#{href}">) +
                    %(</head><body><a href="#{href}">Submit a dataset</a></body></html>)
        p.data = {}
      end
      DOMAINS.each do |key, (label, stem)|
        site.pages << DomainPage.new(site, key, label, stem, records.select { |r| r["domain"] == key })
      end
    end
  end

  module Filters
    # URL of a dataset page.
    def dataset_url(identifier)
      "#{@context.registers[:site].baseurl}/dataset/#{LODCloud.url_path(identifier.to_s)}/"
    end

    # URL of the dataset's metadata in a given format: json, rdf (RDF/XML),
    # ttl (Turtle) or nt (N-Triples).
    def format_url(identifier, format)
      "#{@context.registers[:site].baseurl}/#{format}/#{LODCloud.url_path(identifier.to_s)}"
    end

    # Name of the record's file in data/datasets, percent-encoded for use in a URL.
    def dataset_file(identifier)
      ERB::Util.url_encode(LODCloud.filename(identifier.to_s))
    end

    # Data comes from pull requests, so never emit a URL with another scheme
    # (e.g. javascript:) into an href or src.
    def safe_url(url)
      url.to_s.match?(%r{\A(https?|ftp)://\S+\z}i) ? url.to_s : ""
    end

    def thousands(number)
      number.to_s.reverse.scan(/\d{1,3}/).join(",").reverse
    end

    def domain_label(domain)
      DOMAINS.fetch(domain.to_s, [domain.to_s]).first
    end
  end
end

Liquid::Template.register_filter(LODCloud::Filters)
