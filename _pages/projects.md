---
layout: page
title: notes & projects
permalink: /projects/
description: some notes and projects
nav: true
nav_order: 2
display_categories: [projects, talks & notes]
---

<div class="projects">
  {%- for category in page.display_categories %}
  <h2 class="category">{{ category }}</h2>
  {%- assign sorted_projects = site.projects | where: "category", category | sort: "importance" -%}
  <div class="grid">
    {%- for project in sorted_projects -%}
      {% include projects.html %}
    {%- endfor %}
  </div>
  {% endfor %}
</div>
