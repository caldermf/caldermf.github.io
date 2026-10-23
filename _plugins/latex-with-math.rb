require 'bibtex'
require 'latex/decode'

module BibTeX
  module Filters
    # Decode accents and typography while leaving inline math for MathJax.
    class LaTeXWithMath < Filter
      def apply(value)
        expressions = []
        text = value.to_s.gsub(/(?<!\\)\$.*?(?<!\\)\$/m) do |expression|
          expressions << expression
          "BIBTEXMATHPLACEHOLDER#{expressions.length - 1}END"
        end
        ::LaTeX.decode(text).gsub(/BIBTEXMATHPLACEHOLDER(\d+)END/) do
          expressions[Regexp.last_match(1).to_i]
        end
      end
    end
  end
end
