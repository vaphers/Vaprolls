package parser

import (
	"crypto/md5"
	"encoding/hex"
	"io"
	"math"
	"net/url"
	"path"
	"regexp"
	"strconv"
	"strings"

	"golang.org/x/net/html"
	"golang.org/x/net/html/atom"
)

var (
	sentenceRegex = regexp.MustCompile(`[\.\!\?]+`)
	spaceRegex    = regexp.MustCompile(`\s+`)
)

// StreamParser performs single-pass HTML tokenization and extracts all SEO metadata
type StreamParser struct{}

// NewStreamParser creates a new HTML parser
func NewStreamParser() *StreamParser {
	return &StreamParser{}
}

// Parse extracts all SEO metadata, links, images, headings, and signals from an HTML reader
func (p *StreamParser) Parse(r io.Reader, baseURL string) (*PageParseResult, error) {
	z := html.NewTokenizer(r)

	res := &PageParseResult{
		H1H6:        make(map[string][]string),
		OGTags:      make(map[string]string),
		TwitterTags: make(map[string]string),
	}

	var (
		currentTag       atom.Atom
		inTitle          bool
		inH1             bool
		inH2             bool
		inH3             bool
		inH4             bool
		inH5             bool
		inH6             bool
		inScriptJSONLD   bool
		currentHeading   strings.Builder
		currentJSONLD    strings.Builder
		bodyText         strings.Builder
		currentLinkTag   string
		currentLinkHREF  string
		currentLinkRel   string
		currentLinkLang  string
		currentLinkText  strings.Builder
		inAnchor         bool
		currentForm      *FormData
		inForm           bool
		rawBytesCount    int
	)

	baseParsed, _ := url.Parse(baseURL)

	for {
		tt := z.Next()
		if tt == html.ErrorToken {
			err := z.Err()
			if err == io.EOF {
				break
			}
			// Non-fatal, break loop on token error
			break
		}

		rawBytesCount += len(z.Raw())

		switch tt {
		case html.StartTagToken, html.SelfClosingTagToken:
			tok := z.Token()
			currentTag = tok.DataAtom

			attrs := make(map[string]string, len(tok.Attr))
			for _, a := range tok.Attr {
				attrs[strings.ToLower(a.Key)] = a.Val
			}

			switch currentTag {
			case atom.Html:
				if lang, ok := attrs["lang"]; ok && res.Language == "" {
					res.Language = strings.TrimSpace(lang)
				}

			case atom.Title:
				inTitle = true

			case atom.Meta:
				name := strings.ToLower(attrs["name"])
				property := strings.ToLower(attrs["property"])
				content := strings.TrimSpace(attrs["content"])
				httpEquiv := strings.ToLower(attrs["http-equiv"])

				if name == "description" && res.MetaDescription == "" {
					res.MetaDescription = content
				} else if name == "keywords" && res.MetaKeywords == "" {
					res.MetaKeywords = content
				} else if name == "robots" && res.MetaRobots == "" {
					res.MetaRobots = content
				} else if name == "viewport" && res.Viewport == "" {
					res.Viewport = content
				} else if httpEquiv == "content-language" && res.Language == "" {
					res.Language = content
				}

				// OpenGraph
				if strings.HasPrefix(property, "og:") {
					res.OGTags[property] = content
				}

				// Twitter Cards
				if strings.HasPrefix(name, "twitter:") {
					res.TwitterTags[name] = content
				}

			case atom.Link:
				rel := strings.ToLower(attrs["rel"])
				href := strings.TrimSpace(attrs["href"])

				if strings.Contains(rel, "canonical") && res.CanonicalURL == "" {
					res.CanonicalURL = resolveReference(baseParsed, href)
				} else if strings.Contains(rel, "alternate") {
					hreflang := strings.TrimSpace(attrs["hreflang"])
					if hreflang != "" && href != "" {
						res.HreflangTags = append(res.HreflangTags, HreflangData{
							LangCode:  hreflang,
							TargetURL: resolveReference(baseParsed, href),
						})
					}
				} else if rel == "prev" || rel == "next" {
					if href != "" {
						res.PaginationTags = append(res.PaginationTags, PaginationData{
							RelType:   rel,
							TargetURL: resolveReference(baseParsed, href),
							Source:    "html",
						})
					}
				}

			case atom.H1:
				inH1 = true
				currentHeading.Reset()
			case atom.H2:
				inH2 = true
				currentHeading.Reset()
			case atom.H3:
				inH3 = true
				currentHeading.Reset()
			case atom.H4:
				inH4 = true
				currentHeading.Reset()
			case atom.H5:
				inH5 = true
				currentHeading.Reset()
			case atom.H6:
				inH6 = true
				currentHeading.Reset()

			case atom.A, atom.Area:
				href := strings.TrimSpace(attrs["href"])
				if href != "" {
					inAnchor = true
					currentLinkTag = tok.Data
					currentLinkHREF = href
					currentLinkRel = attrs["rel"]
					currentLinkLang = attrs["hreflang"]
					currentLinkText.Reset()
				}

			case atom.Img:
				src := strings.TrimSpace(attrs["src"])
				if src != "" {
					w, _ := strconv.Atoi(attrs["width"])
					h, _ := strconv.Atoi(attrs["height"])
					ext := strings.ToLower(path.Ext(src))
					if len(ext) > 1 {
						ext = ext[1:]
					}

					isLazy := strings.Contains(strings.ToLower(attrs["loading"]), "lazy")
					res.Images = append(res.Images, ImageData{
						Src:          resolveReference(baseParsed, src),
						Alt:          attrs["alt"],
						Width:        w,
						Height:       h,
						Format:       ext,
						IsLazyLoaded: isLazy,
					})
				}

			case atom.Iframe:
				src := strings.TrimSpace(attrs["src"])
				if src != "" {
					res.Iframes = append(res.Iframes, IframeData{
						Src:     resolveReference(baseParsed, src),
						Title:   attrs["title"],
						Loading: attrs["loading"],
					})
				}

			case atom.Form:
				inForm = true
				action := strings.TrimSpace(attrs["action"])
				method := strings.ToUpper(strings.TrimSpace(attrs["method"]))
				if method == "" {
					method = "GET"
				}
				currentForm = &FormData{
					Action: action,
					Method: method,
					ID:     attrs["id"],
				}

			case atom.Input:
				if inForm && currentForm != nil {
					inputType := strings.ToLower(attrs["type"])
					if inputType == "password" {
						currentForm.HasPassword = true
					} else if inputType == "search" || strings.Contains(strings.ToLower(attrs["name"]), "search") {
						currentForm.IsSearch = true
					}
				}

			case atom.Script:
				scriptType := strings.ToLower(attrs["type"])
				if scriptType == "application/ld+json" {
					inScriptJSONLD = true
					currentJSONLD.Reset()
				}
			}

		case html.TextToken:
			text := z.Token().Data

			if inTitle {
				if res.Title == "" {
					res.Title = strings.TrimSpace(text)
				} else {
					res.Title += " " + strings.TrimSpace(text)
				}
			}

			if inH1 || inH2 || inH3 || inH4 || inH5 || inH6 {
				currentHeading.WriteString(text)
				currentHeading.WriteString(" ")
			}

			if inAnchor {
				currentLinkText.WriteString(text)
				currentLinkText.WriteString(" ")
			}

			if inScriptJSONLD {
				currentJSONLD.WriteString(text)
			}

			// Collect visible body text (skipping style and non-jsonld script)
			if currentTag != atom.Style && (!inScriptJSONLD && currentTag != atom.Script) {
				cleanText := strings.TrimSpace(text)
				if cleanText != "" {
					bodyText.WriteString(cleanText)
					bodyText.WriteString(" ")
				}
			}

		case html.EndTagToken:
			tok := z.Token()
			endTag := tok.DataAtom

			switch endTag {
			case atom.Title:
				inTitle = false
				res.Title = strings.TrimSpace(res.Title)
				res.TitleLength = len(res.Title)

			case atom.H1:
				inH1 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h1"] = append(res.H1H6["h1"], txt)
				}
			case atom.H2:
				inH2 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h2"] = append(res.H1H6["h2"], txt)
				}
			case atom.H3:
				inH3 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h3"] = append(res.H1H6["h3"], txt)
				}
			case atom.H4:
				inH4 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h4"] = append(res.H1H6["h4"], txt)
				}
			case atom.H5:
				inH5 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h5"] = append(res.H1H6["h5"], txt)
				}
			case atom.H6:
				inH6 = false
				txt := strings.TrimSpace(currentHeading.String())
				if txt != "" {
					res.H1H6["h6"] = append(res.H1H6["h6"], txt)
				}

			case atom.A, atom.Area:
				if inAnchor {
					inAnchor = false
					linkText := strings.TrimSpace(currentLinkText.String())
					relLower := strings.ToLower(currentLinkRel)
					noFollow := strings.Contains(relLower, "nofollow")

					resolvedHREF := currentLinkHREF
					isInternal := false
					if baseParsed != nil {
						rel, err := url.Parse(currentLinkHREF)
						if err == nil {
							resolved := baseParsed.ResolveReference(rel)
							resolvedHREF = resolved.String()
							d1 := strings.ToLower(baseParsed.Hostname())
							d2 := strings.ToLower(resolved.Hostname())
							d1 = strings.TrimPrefix(d1, "www.")
							d2 = strings.TrimPrefix(d2, "www.")
							isInternal = (d1 == d2 || d2 == "")
						}
					}

					res.Links = append(res.Links, LinkData{
						Tag:        currentLinkTag,
						HREF:       resolvedHREF,
						Rel:        currentLinkRel,
						Hreflang:   currentLinkLang,
						Text:       linkText,
						IsInternal: isInternal,
						NoFollow:   noFollow,
					})
				}

			case atom.Form:
				if inForm && currentForm != nil {
					inForm = false
					res.Forms = append(res.Forms, *currentForm)
					currentForm = nil
				}

			case atom.Script:
				if inScriptJSONLD {
					inScriptJSONLD = false
					jsonldStr := strings.TrimSpace(currentJSONLD.String())
					if jsonldStr != "" {
						res.StructuredData = append(res.StructuredData, jsonldStr)
					}
				}
			}
		}
	}

	// Post-processing
	res.MetaDescriptionLength = len(res.MetaDescription)
	res.MetaKeywordsLength = len(res.MetaKeywords)

	if len(res.H1H6["h1"]) > 0 {
		res.H1 = res.H1H6["h1"][0]
		res.H1Count = len(res.H1H6["h1"])
		res.H1Length = len(res.H1)
	}
	if len(res.H1H6["h2"]) > 0 {
		res.H2 = res.H1H6["h2"][0]
		res.H2Count = len(res.H1H6["h2"])
		res.H2Length = len(res.H2)
	}

	fullText := bodyText.String()
	rawWords := strings.Fields(fullText)
	var words []string
	for _, w := range rawWords {
		clean := strings.TrimSpace(w)
		if clean != "" {
			words = append(words, clean)
		}
	}

	res.WordCount = len(words)

	// MD5 Content Hash
	hasher := md5.New()
	hasher.Write([]byte(strings.Join(words, " ")))
	res.ContentHash = hex.EncodeToString(hasher.Sum(nil))

	// SimHash
	simVal := ComputeSimHash(fullText)
	res.SimHash = FormatSimHash(simVal)

	// Readability & Sentence Count
	rawSentences := sentenceRegex.Split(fullText, -1)
	var validSentences int
	for _, s := range rawSentences {
		if len(strings.TrimSpace(s)) > 3 {
			validSentences++
		}
	}
	res.SentenceCount = validSentences
	if res.SentenceCount > 0 {
		res.AvgWordsPerSentence = math.Round((float64(res.WordCount)/float64(res.SentenceCount))*100) / 100
	}
	if rawBytesCount > 0 {
		res.TextRatio = math.Round((float64(len(strings.TrimSpace(fullText)))/float64(rawBytesCount))*10000) / 100
	}

	return res, nil
}

func resolveReference(base *url.URL, ref string) string {
	ref = strings.TrimSpace(ref)
	if ref == "" || base == nil {
		return ref
	}
	rel, err := url.Parse(ref)
	if err != nil {
		return ref
	}
	return base.ResolveReference(rel).String()
}
