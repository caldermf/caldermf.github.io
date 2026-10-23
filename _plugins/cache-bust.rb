require 'digest/md5'

module Jekyll
  module CacheBust
    def bust_file_cache(file_name)
      path = file_name[file_name.index('assets/')..-1]
      "#{file_name}?#{Digest::MD5.file(path).hexdigest}"
    end

    def bust_css_cache(file_name)
      sources = ['assets/css/main.scss', *Dir['_sass/**/*.scss'].sort]
      digest = Digest::MD5.hexdigest(sources.map { |path| File.read(path) }.join)
      "#{file_name}?#{digest}"
    end
  end
end

Liquid::Template.register_filter(Jekyll::CacheBust)
