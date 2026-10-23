---
layout: page
title: Projects & notes
permalink: /projects/
description:
seo_title: "Research Software, Projects & Notes | Calder Morton-Ferguson"
seo_description: "Explore Calder Morton-Ferguson's research software, interactive Burnside sampler, mathematical visualizations, talks, and notes."
nav: true
nav_order: 2
display_categories: [projects, talks & notes]
---

{% for category in page.display_categories -%}
<section class="project-group">
  <h2>{{ category | capitalize }}</h2>
  {%- assign sorted_projects = site.projects | where: "category", category | sort: "importance" %}
  <ul class="project-list">
    {%- for project in sorted_projects %}
    {% include projects.html %}
    {%- endfor %}
  </ul>
</section>
{% endfor %}
