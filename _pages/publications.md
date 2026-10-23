---
layout: page
permalink: /publications/
title: publications
description: papers listed by first arXiv posting, newest first.
seo_title: "Research Publications | Calder Morton-Ferguson"
seo_description: "Research papers by Calder Morton-Ferguson on language-model reasoning, geometric representation theory, algebra, and combinatorics, with abstracts and links."
nav: true
nav_order: 1
---
<!-- _pages/publications.md -->
<div class="publications">

{% include publication_filters.html %}

{% bibliography -f {{ site.scholar.bibliography }} %}

</div>

<p><a href="{{ '/publications.bib' | relative_url }}" download>Download the bibliography (BibTeX)</a></p>
