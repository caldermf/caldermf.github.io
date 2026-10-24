---
layout: page
title: Projects & Notes
permalink: /projects/
description:
seo_description: "Research code, an interactive Burnside sampler, and notes from talks."
nav: true
nav_order: 2
display_categories:
  - category: projects
    title: Projects
  - category: talks & notes
    title: Talks & Notes
---

{% for group in page.display_categories -%}
<h2 class="list-head">{{ group.title }}</h2>
{%- assign sorted_projects = site.projects | where: "category", group.category | sort: "importance" %}
<ul class="project-list">
  {%- for project in sorted_projects %}
  {% include projects.html %}
  {%- endfor %}
</ul>
{% endfor %}
