FROM ruby:3.3-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git imagemagick libyaml-dev nodejs pkg-config \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/jekyll
ENV LANG=C.UTF-8 \
    JEKYLL_ENV=development \
    EXECJS_RUNTIME=Node \
    BUNDLE_IGNORE_CONFIG=1

COPY Gemfile* ./
RUN bundle install --jobs 4 --retry 3
# Catch plugin/native-library load errors before starting the preview container.
RUN bundle exec ruby -rjekyll -rexecjs -e 'Jekyll::PluginManager.require_from_bundler; abort "JavaScript runtime check failed" unless ExecJS.eval("1 + 1") == 2'

COPY bin/docker-entrypoint /usr/local/bin/site-entrypoint
ENTRYPOINT ["/bin/sh", "/usr/local/bin/site-entrypoint"]
EXPOSE 8080 35729
CMD ["bundle", "exec", "jekyll", "serve", "--host", "0.0.0.0", "--port", "8080", "--livereload", "--force_polling"]
