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

  class DatasetPage < Jekyll::PageWithoutAFile
    def initialize(site, record)
      @identifier = record["identifier"]
      raise "Invalid dataset identifier #{@identifier.inspect}" if [".", ".."].include?(@identifier)

      super(site, site.source, File.join("dataset", @identifier), "index.html")
      @content = ""
      @data = { "layout" => "dataset", "title" => record["title"], "dataset" => record }
    end

    # Jekyll's URL handling rewrites some identifiers (e.g. one ending in "."),
    # so place the page explicitly: /dataset/<identifier>/index.html.
    def url
      "/dataset/#{ERB::Util.url_encode(@identifier)}/"
    end

    def destination(dest)
      File.join(dest, "dataset", @identifier, "index.html")
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

      records.each { |r| site.pages << DatasetPage.new(site, r) }
      DOMAINS.each do |key, (label, stem)|
        site.pages << DomainPage.new(site, key, label, stem, records.select { |r| r["domain"] == key })
      end
    end
  end

  module Filters
    # URL of a dataset page, percent-encoding any identifier.
    def dataset_url(identifier)
      "#{@context.registers[:site].baseurl}/dataset/#{ERB::Util.url_encode(identifier.to_s)}/"
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
