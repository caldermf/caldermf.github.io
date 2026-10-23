require 'jekyll/scholar'

module ArxivYearGrouping
  def group_value(key, entry)
    return super unless key == 'arxiv_year'

    # Modern arXiv IDs encode the original YYMM, unchanged by revisions.
    match = /\A(\d{2})(?:0[1-9]|1[0-2])\.\d{4,5}(?:v\d+)?\z/.match(entry[:arxiv].to_s)
    match ? "20#{match[1]}" : super('year', entry)
  end
end

Jekyll::Scholar::Utilities.prepend(ArxivYearGrouping)
