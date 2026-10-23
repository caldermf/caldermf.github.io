require 'bibtex'
require 'date'
require 'fileutils'
require 'json'
require 'latex/decode'
require 'open3'
require 'uri'

module ResearchSite
  NAME = 'Calder Morton-Ferguson'.freeze

  # Raw data exports must bypass Markdown/BibTeX HTML converters.
  class ExportFile < Jekyll::StaticFile
    def initialize(site, path, content)
      super(site, site.source, '', path)
      @content = content
    end

    def data
      { 'sitemap' => false }
    end

    def write(destination_root)
      target = destination(destination_root)
      FileUtils.mkdir_p(File.dirname(target))
      File.write(target, @content)
      true
    end
  end

  def self.text(value)
    LaTeX.decode(value.to_s).gsub(/\s+/, ' ').strip
  end

  def self.absolute(site, path)
    return path if path.to_s.match?(%r{\Ahttps?://})
    "#{site.config['url'].sub(%r{/$}, '')}#{site.config['baseurl']}/#{path.to_s.sub(%r{\A/}, '')}"
  end

  module Filters
    def safe_json(value)
      JSON.generate(value).gsub('<', '\\u003c').gsub('>', '\\u003e').gsub('&', '\\u0026')
    end

    def image_dimensions(path)
      site = @context.registers[:site]
      file = File.join(site.source, path.to_s.sub(%r{\A/}, ''))
      return nil unless File.file?(file)
      site.data['image_dimensions'] ||= {}
      site.data['image_dimensions'][path] ||= begin
        output, _, status = Open3.capture3('identify', '-format', '%w %h', "#{file}[0]")
        status.success? ? output.split.map(&:to_i) : nil
      end
    end
  end

  class Generator < Jekyll::Generator
    priority :low

    def generate(site)
      @site = site
      @person = person
      bib = BibTeX.open(File.join(site.source, '_bibliography', site.config.dig('scholar', 'bibliography')))
      bib.replace_strings
      bib.join
      @papers = bib.entries.values.map { |entry| paper(entry) }.sort_by { |p| p['arxiv'].sub(/v\d+$/, '') }.reverse
      site.data['papers_by_key'] = @papers.to_h { |p| [p['key'], p] }
      @papers.each { |p| publication_page(p) }
      exports(bib)
      (site.pages + site.collections.values.flat_map(&:docs)).each do |page|
        next unless page.data['layout'] || page.data['seo_enabled']
        metadata(page)
      end
    end

    def url(path)
      ResearchSite.absolute(@site, path)
    end

    def person
      {
        '@type' => 'Person', '@id' => url('/#person'), 'name' => NAME,
        'url' => url('/'), 'image' => url(@site.config['social_image']),
        'description' => @site.config['description'],
        'jobTitle' => ['Mathematician', 'Research scientist'],
        'knowsAbout' => ['Machine learning', 'Reasoning in language models', 'Geometric representation theory', 'Algebra', 'Geometry', 'Combinatorics'],
        'alumniOf' => { '@type' => 'CollegeOrUniversity', 'name' => 'Massachusetts Institute of Technology' },
        'sameAs' => [
          "https://orcid.org/#{@site.config['orcid_id']}",
          "https://scholar.google.com/citations?user=#{@site.config['scholar_userid']}",
          "https://github.com/#{@site.config['github_username']}",
          "https://www.linkedin.com/in/#{@site.config['linkedin_username']}/"
        ]
      }
    end

    def paper(entry)
      title = ResearchSite.text(entry[:title])
      authors = entry.author.map do |author|
        ResearchSite.text([author.first, author.prefix, author.last, author.suffix].compact.join(' '))
      end
      arxiv = entry[:arxiv].to_s
      first_posted = entry[:arxiv_date].to_s
      # Dates are verified once against arXiv, never inferred as an invented day.
      Date.iso8601(first_posted) unless first_posted.empty?
      is_appendix = title.start_with?('Appendix to')
      subject_ids = entry[:subjects].to_s.split(',').map(&:strip)
      taxonomy = @site.data.fetch('publication_subjects')
      unknown_subjects = subject_ids - taxonomy.map { |subject| subject['id'] }
      raise "Unknown subjects for #{entry.key}: #{unknown_subjects.join(', ')}" unless unknown_subjects.empty?
      data = {
        'key' => entry.key, 'title' => title, 'authors' => authors,
        'subjects' => taxonomy.select { |subject| subject_ids.include?(subject['id']) },
        'abstract' => BibTeX::Filters::LaTeXWithMath.instance.apply(entry[:abstract].to_s),
        'arxiv' => arxiv, 'arxiv_url' => "https://arxiv.org/abs/#{arxiv}",
        'arxiv_date' => first_posted, 'citation_year' => entry[:year].to_s,
        'url' => "/publications/#{entry.key.downcase}/", 'is_appendix' => is_appendix,
        'pdf_url' => "https://arxiv.org/pdf/#{arxiv}",
        'preview' => entry[:preview] && "/assets/img/publication_preview/#{entry[:preview]}",
        'preview_alt' => entry[:preview_alt]&.to_s || "Figure from #{title}",
        'journal' => entry[:journal] && ResearchSite.text(entry[:journal]),
        'doi' => entry[:doi]&.to_s, 'volume' => entry[:volume]&.to_s,
        'issue' => entry[:number]&.to_s, 'pages' => entry[:pages]&.to_s,
        'publisher_url' => entry[:html]&.to_s, 'code_url' => entry[:github]&.to_s
      }.compact
      if data['pages']
        pages = data['pages'].split(/--|–|-/, 2)
        data['first_page'] = pages.first
        data['last_page'] = pages.last if pages.length == 2
      end
      data['publication_details'] = [data['journal'], data['volume'] && "vol. #{data['volume']}", data['issue'] && "no. #{data['issue']}", data['pages'] && "pp. #{data['pages']}", data['citation_year']].compact.join(', ')
      data['schema'] = article_schema(data)
      data
    end

    def article_schema(p)
      schema = {
        '@type' => p['is_appendix'] ? 'Chapter' : 'ScholarlyArticle',
        '@id' => url("#{p['url']}#work"), 'url' => url(p['url']),
        'name' => p['title'], 'headline' => p['title'],
        'keywords' => p['subjects'].map { |subject| subject['label'] },
        'author' => p['authors'].map { |name| name == NAME ? { '@id' => @person['@id'], '@type' => 'Person', 'name' => name } : { '@type' => 'Person', 'name' => name } },
        'inLanguage' => 'en', 'mainEntityOfPage' => { '@id' => url("#{p['url']}#webpage") }
      }
      unless p['abstract'].empty?
        schema['abstract'] = p['abstract']
      end
      schema['image'] = url(p['preview']) if p['preview']
      if p['is_appendix']
        # The arXiv ID/DOI describe the parent paper, not this three-author appendix.
        schema['isPartOf'] = { '@type' => 'ScholarlyArticle', 'name' => p['title'].sub(/\AAppendix to /, '').delete('"'), 'url' => p['arxiv_url'] }
      else
        schema['datePublished'] = p['arxiv_date'] unless p['arxiv_date'].empty?
        schema['sameAs'] = [p['arxiv_url'], p['doi'] && "https://doi.org/#{p['doi']}"].compact
        schema['identifier'] = { '@type' => 'PropertyValue', 'propertyID' => 'arXiv', 'value' => p['arxiv'].sub(/v\d+$/, '') }
        schema['isPartOf'] = { '@type' => 'Periodical', 'name' => p['journal'] } if p['journal']
      end
      schema
    end

    def add_page(path, content, data = {})
      page = Jekyll::PageWithoutAFile.new(@site, @site.source, File.dirname(path), File.basename(path))
      page.content = content
      page.data.merge!(data)
      @site.pages << page
      page
    end

    def publication_page(p)
      description = p['abstract'].empty? ? "#{p['title']} by #{p['authors'].join(', ')}. Publication details and links to the full paper." : p['abstract'].gsub(/\s+/, ' ')[0, 155].sub(/\s+\S*\z/, '') + '…'
      add_page("#{p['url'].delete_prefix('/')}index.html", '', {
        'layout' => 'publication', 'title' => p['title'], 'paper' => p,
        'seo_description' => description, 'social_image' => p['preview'],
        'social_image_alt' => p['preview_alt'], 'sitemap' => true
      })
    end

    def export(path, content)
      @site.static_files << ExportFile.new(@site, path, content)
    end

    def exports(bib)
      export('profile.json', JSON.pretty_generate({ '@context' => 'https://schema.org' }.merge(@person)))
      export('publications.json', JSON.pretty_generate({
        'author' => NAME, 'url' => url('/publications/'), 'ordering' => 'First arXiv posting, newest first',
        'publications' => @papers.map { |p| p.reject { |key, _| key == 'schema' }.merge('url' => url(p['url'])) }
      }))
      markdown = "# Publications by #{NAME}\n\nListed by first arXiv posting, newest first. Journal publication dates are separate.\n\n"
      @papers.each do |p|
        markdown << "## #{p['title']}\n\n#{p['authors'].join(', ')}\n\n"
        markdown << "Subjects: #{p['subjects'].map { |subject| subject['label'] }.join(', ')}\n\n"
        markdown << "#{p['is_appendix'] ? 'Parent paper first posted' : 'First posted'} on arXiv: #{p['arxiv_date']}\n\n"
        markdown << "Journal publication: #{p['publication_details']}\n\n" if p['journal']
        markdown << "#{p['abstract']}\n\n" unless p['abstract'].empty?
        markdown << "[Details](#{url(p['url'])}) · [arXiv](#{p['arxiv_url']}) · [PDF](#{p['pdf_url']})\n\n"
      end
      export('publications.md', markdown)
      allowed = %i[author title year month journal booktitle volume number pages doi issn url arxiv archiveprefix primaryclass]
      bibtext = bib.entries.values.map do |entry|
        fields = entry.fields.select { |key, _| allowed.include?(key) }
        fields[:eprint] = entry[:arxiv] unless ResearchSite.text(entry[:title]).start_with?('Appendix to')
        "@#{entry.type}{#{entry.key},\n" + fields.map { |key, value| "  #{key} = {#{value}}" }.join(",\n") + "\n}\n"
      end.join("\n")
      export('publications.bib', bibtext)
      links = <<~TEXT
        # #{NAME}

        > #{@site.config['description']}

        This is Calder Morton-Ferguson's personal research website. Researcher identity is also linked through ORCID, Google Scholar, GitHub, and LinkedIn on the homepage.

        ## Main pages
        - [Biography and publications](#{url('/')}): Current research interests, academic background, and the full publication list.
        - [Publications](#{url('/publications/')}): Papers grouped by original arXiv year; journal publication dates are listed separately.
        - [Research software and notes](#{url('/projects/')}): Projects, interactive demonstrations, talks, and notes.
        - [Teaching](#{url('/teaching/')}): Mathematics teaching experience.
        - [CV](#{url('/assets/pdf/cv.pdf')}): Academic CV in PDF format.

        ## Structured and plain-text research data
        - [Researcher profile](#{url('/profile.json')}): Schema.org Person data with verified profile links.
        - [Publication data](#{url('/publications.json')}): Titles, authors, original arXiv dates, abstracts, journal details, and source links.
        - [Publications in Markdown](#{url('/publications.md')}): Readable paper summaries and abstracts.
        - [BibTeX bibliography](#{url('/publications.bib')}): Bibliographic records retaining journal publication years.

        ## Papers
      TEXT
      @papers.each { |p| links << "- [#{p['title']}](#{url(p['url'])}): #{p['authors'].join(', ')}.\n" }
      export('llms.txt', links)
    end

    def metadata(page)
      home = page.url == '/'
      title = page.data['seo_title'] || (home ? @site.config['seo_title'] : "#{page.data['title']} | #{NAME}")
      description = [page.data['seo_description'], page.data['description'], @site.config['description']].find { |text| !text.to_s.strip.empty? }.to_s
      canonical = url(page.data['canonical_url'] || page.url.sub(%r{/index\.html$}, '/'))
      page.data['seo'] = {
        'title' => title, 'description' => description, 'canonical' => canonical,
        'image' => url(page.data['social_image'] || page.data['img'] || @site.config['social_image']),
        'image_alt' => page.data['social_image_alt'] || (page.data['img'] ? "#{page.data['title']} project illustration" : "Portrait of #{NAME}")
      }
      return if page.data['noindex']
      website = { '@type' => 'WebSite', '@id' => url('/#website'), 'url' => url('/'), 'name' => NAME, 'inLanguage' => 'en', 'publisher' => { '@id' => @person['@id'] } }
      webpage = {
        '@type' => home ? 'ProfilePage' : (['/publications/', '/projects/'].include?(page.url) ? 'CollectionPage' : 'WebPage'),
        '@id' => "#{canonical}#webpage", 'url' => canonical, 'name' => title, 'description' => description,
        'inLanguage' => 'en', 'isPartOf' => { '@id' => website['@id'] }, 'about' => { '@id' => @person['@id'] }
      }
      graph = [website, @person, webpage]
      if home
        webpage['mainEntity'] = { '@id' => @person['@id'] }
      elsif page.data['paper']
        graph << page.data['paper']['schema']
        webpage['mainEntity'] = { '@id' => page.data['paper']['schema']['@id'] }
      elsif page.url == '/publications/'
        graph << {
          '@type' => 'ItemList', '@id' => "#{canonical}#papers", 'name' => "Research publications by #{NAME}",
          'numberOfItems' => @papers.length,
          'itemListElement' => @papers.each_with_index.map { |p, i| { '@type' => 'ListItem', 'position' => i + 1, 'name' => p['title'], 'url' => url(p['url']) } }
        }
        webpage['mainEntity'] = { '@id' => "#{canonical}#papers" }
      elsif page.url == '/burnside-sampler/web/'
        app = {
          '@type' => 'WebApplication', '@id' => "#{canonical}#application",
          'name' => 'Burnside Process Sampler', 'url' => canonical,
          'description' => description, 'applicationCategory' => 'EducationalApplication',
          'operatingSystem' => 'Web browser', 'isAccessibleForFree' => true,
          'author' => { '@id' => @person['@id'] },
          'isBasedOn' => 'https://github.com/caldermf/burnside-sampler'
        }
        graph << app
        webpage['mainEntity'] = { '@id' => app['@id'] }
      end
      unless home
        crumbs = [{ '@type' => 'ListItem', 'position' => 1, 'name' => NAME, 'item' => url('/') }]
        parent = page.data['paper'] ? ['/publications/', 'Publications'] : (page.url.start_with?('/projects/') && page.url != '/projects/' ? ['/projects/', 'Projects'] : nil)
        crumbs << { '@type' => 'ListItem', 'position' => 2, 'name' => parent[1], 'item' => url(parent[0]) } if parent
        crumbs << { '@type' => 'ListItem', 'position' => crumbs.length + 1, 'name' => page.data['title'], 'item' => canonical }
        graph << { '@type' => 'BreadcrumbList', '@id' => "#{canonical}#breadcrumbs", 'itemListElement' => crumbs }
        webpage['breadcrumb'] = { '@id' => "#{canonical}#breadcrumbs" }
      end
      page.data['structured_data'] = { '@context' => 'https://schema.org', '@graph' => graph }
    end
  end
end

Liquid::Template.register_filter(ResearchSite::Filters)
