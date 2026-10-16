package parser

// LinkData represents an extracted hyperlink
type LinkData struct {
	Tag        string `json:"tag"`
	HREF       string `json:"href"`
	Rel        string `json:"rel"`
	Hreflang   string `json:"hreflang"`
	Text       string `json:"text"`
	IsInternal bool   `json:"is_internal"`
	NoFollow   bool   `json:"nofollow"`
}

// ImageData represents an extracted <img> tag
type ImageData struct {
	Src          string `json:"src"`
	Alt          string `json:"alt"`
	Width        int    `json:"width"`
	Height       int    `json:"height"`
	Format       string `json:"format"`
	IsLazyLoaded bool   `json:"is_lazy_loaded"`
}

// HreflangData represents a rel="alternate" hreflang tag
type HreflangData struct {
	LangCode  string `json:"lang_code"`
	TargetURL string `json:"target_url"`
}

// PaginationData represents rel="prev" or rel="next" links
type PaginationData struct {
	RelType   string `json:"rel_type"`
	TargetURL string `json:"target_url"`
	Source    string `json:"source"` // "html" or "http_header"
}

// FormData represents a discovered form
type FormData struct {
	Action      string `json:"action"`
	Method      string `json:"method"`
	ID          string `json:"id"`
	HasPassword bool   `json:"has_password"`
	IsSearch    bool   `json:"is_search"`
	IsInsecure  bool   `json:"is_insecure"`
}

// IframeData represents an embedded iframe
type IframeData struct {
	Src     string `json:"src"`
	Title   string `json:"title"`
	Loading string `json:"loading"`
}

// PageParseResult contains all parsed SEO data extracted from a page
type PageParseResult struct {
	Title                 string              `json:"title"`
	TitleLength           int                 `json:"title_length"`
	MetaDescription       string              `json:"meta_description"`
	MetaDescriptionLength int                 `json:"meta_description_length"`
	MetaKeywords          string              `json:"meta_keywords"`
	MetaKeywordsLength    int                 `json:"meta_keywords_length"`
	MetaRobots            string              `json:"meta_robots"`
	CanonicalURL          string              `json:"canonical_url"`
	Viewport              string              `json:"viewport"`
	Language              string              `json:"language"`
	H1H6                  map[string][]string `json:"h1_h6"`
	H1                    string              `json:"h1"`
	H1Count               int                 `json:"h1_count"`
	H1Length              int                 `json:"h1_length"`
	H2                    string              `json:"h2"`
	H2Count               int                 `json:"h2_count"`
	H2Length              int                 `json:"h2_length"`
	WordCount             int                 `json:"word_count"`
	SentenceCount         int                 `json:"sentence_count"`
	AvgWordsPerSentence   float64             `json:"avg_words_per_sentence"`
	TextRatio             float64             `json:"text_ratio"`
	ContentHash           string              `json:"content_hash"`
	SimHash               string              `json:"simhash"`
	Links                 []LinkData          `json:"links"`
	Images                []ImageData         `json:"images"`
	StructuredData        []string            `json:"structured_data"`
	OGTags                map[string]string   `json:"og_tags"`
	TwitterTags           map[string]string   `json:"twitter_tags"`
	HreflangTags          []HreflangData      `json:"hreflang_tags"`
	PaginationTags        []PaginationData    `json:"pagination_tags"`
	Forms                 []FormData          `json:"forms"`
	Iframes               []IframeData        `json:"iframes"`
}
