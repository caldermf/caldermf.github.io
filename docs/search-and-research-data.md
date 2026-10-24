# Search and research data maintenance

The site remains static HTML. Titles, abstracts, links, and researcher identity are readable without JavaScript. JSON-LD describes the same visible content; it does not add employment claims or expose the email address in structured form.

## Sources of truth

- `_pages/about.md`: approved biography and visible plain-text contact information.
- `_config.yml`: short search description, personal profile identifiers, and social preview image.
- `_bibliography/papers.bib`: paper titles, full author lists, abstracts, journal publication metadata, arXiv IDs, and `arxiv_date` (the verified first submission date shown by arXiv).
- `_projects/*.md`: real project/notes landing pages with links to source code, demonstrations, and documents.
- `_data/cv.yml`: the CV shown at `/cv/`, transcribed from `assets/pdf/cv.pdf`. Update both together.

For new papers, copy the first arXiv submission date, not the latest revision date. Keep the journal's publication year in `year`. The lists derive their grouping from the original arXiv ID; the paper pages distinguish first posting from journal publication. An appendix is represented separately from its parent paper to avoid assigning the appendix's author list to the entire paper.

## Generated outputs

`_plugins/research-site.rb` creates stable `/publications/<bibtex-key>/` pages, structured metadata, `/profile.json`, `/publications.json`, `/publications.md`, `/publications.bib`, and `/llms.txt`. Do not edit those generated files in `_site`. The optional `llms.txt` is a navigation aid, not a search-engine requirement or a ranking guarantee.

The citation meta tags appear only on individual standalone-paper pages, never on the multi-paper list. External PDFs remain linked visibly; no cross-domain `citation_pdf_url` is emitted because Scholar's inclusion guidelines require that metadata URL to share the abstract page's directory. Existing arXiv/journal records remain the primary full-text sources. New local Scholar records are not guaranteed.

`sitemap.xml` includes only indexable pages. It intentionally omits redirect shims, the 404 page, raw research source files, generated data exports, and artificial build timestamps. Add `last_modified_at` only when it reflects a real content update. `/robots.txt` continues to allow crawling for all user agents, including search/retrieval agents; this pass does not change the previous training-crawler policy.

## Validation

After `JEKYLL_ENV=production bundle exec jekyll build`, run:

```sh
bundle exec ruby bin/check-seo _site
```

The deploy workflow runs this check before publishing. It verifies canonical origins, unique titles, descriptions, social metadata, JSON-LD parsing, local URLs/fragments, real responsive-image widths, sitemap coverage, citation author/year consistency, exports, arXiv grouping, social placement, and absence of clickable email links.

For a new build destination, pass it as the first argument. Local Jekyll serve rewrites the site origin to localhost; production validation must use a production build.

## After publishing

- Submit `https://caldermf.github.io/sitemap.xml` through a personal Google Search Console property and Bing Webmaster Tools, then inspect representative URLs. Do not use a business account for this site.
- Test representative paper/profile pages with Google's Rich Results Test and Schema.org's validator. Passing local structural checks does not prove rich-result eligibility.
- Watch real indexing, search queries, and field performance after recrawling; do not infer ranking gains from markup alone.
- Keep descriptions factual and unique. Avoid hidden keywords, fabricated credentials, manufactured modification dates, or mass-generated topic pages.

Primary references:
- https://developers.google.com/search/docs/appearance/ai-features
- https://developers.google.com/search/docs/appearance/structured-data/profile-page
- https://scholar.google.com/intl/en/scholar/inclusion.html
- https://schema.org/ScholarlyArticle
- https://developers.openai.com/api/docs/bots
# Publication subjects

Edit each paper's comma-separated `subjects` field in `_bibliography/papers.bib` using IDs from `_data/publication_subjects.yml`. That file controls filter order and labels, with machine learning first. Tags appear on paper pages, drive the subject filters on both publication lists, and are included in JSON, Markdown, and structured data. Filters select one subject at a time, hide empty years, and update the visible paper count; all papers remain available without JavaScript.

