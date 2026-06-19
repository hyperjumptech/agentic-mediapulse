import newsroom.orchestrator as orchestrator


def test_is_ok_matches_only_leading_ok():
    assert orchestrator._is_ok("OK")
    assert orchestrator._is_ok("ok, looks good")
    assert orchestrator._is_ok("  OK\n")
    assert orchestrator._is_ok("OKAY")
    assert not orchestrator._is_ok("Needs work")
    assert not orchestrator._is_ok("")


def test_humanize_strips_dashes_and_semicolons():
    assert orchestrator._humanize("a — b") == "a, b"
    assert orchestrator._humanize("a; b") == "a, b"
    assert orchestrator._humanize("a ; b , c") == "a, b, c"
    assert orchestrator._humanize("x  —  y") == "x, y"


def test_humanize_keeps_number_ranges_as_hyphen():
    assert orchestrator._humanize("200—250") == "200-250"


def test_is_article_accepts_real_stories():
    assert orchestrator._is_article("https://site.com/news/some-long-article-title")
    assert orchestrator._is_article("https://site.com/one-two-three.html")
    assert orchestrator._is_article("https://site.com/2024123")


def test_is_article_rejects_listings_and_non_articles():
    assert not orchestrator._is_article("https://site.com/")
    assert not orchestrator._is_article("https://site.com/category?cat=tech")
    assert not orchestrator._is_article("https://site.com/list?page=2")
    assert not orchestrator._is_article("https://site.com/a")
    assert not orchestrator._is_article("https://site.com/foo.html")
    assert not orchestrator._is_article("ftp://x/y")
    assert not orchestrator._is_article("not a url")


def test_canonical_url_lowercases_drops_www_query_and_trailing_slash():
    assert orchestrator._canonical_url("https://WWW.Site.com/A/b/?x=1") == "site.com/a/b"
    assert orchestrator._canonical_url("http://site.com/path/") == "site.com/path"


def test_content_key_keeps_only_significant_words():
    key = orchestrator._content_key("Apple buys the BIG startup")
    assert "apple" in key
    assert "startup" in key
    assert "the" not in key  # len <= 3 dropped
    assert "big" not in key


def test_too_similar_detects_high_overlap():
    first = orchestrator._content_key("Apple buys startup company today")
    second = orchestrator._content_key("Apple buys startup company now")
    assert orchestrator._too_similar(first, [second])


def test_too_similar_false_for_empty_or_distinct():
    assert not orchestrator._too_similar(orchestrator._content_key("alpha beta"), [])
    distinct = orchestrator._content_key("totally unrelated different words here")
    other = orchestrator._content_key("apple banana cherry mango orange")
    assert not orchestrator._too_similar(distinct, [other])


def test_first_sentences_keeps_one_sentence():
    assert orchestrator._first_sentences("One. Two. Three.") == "One."


def test_first_sentences_does_not_split_inside_a_number():
    assert orchestrator._first_sentences("0.5% rose. Next.") == "0.5% rose."


def test_first_sentences_caps_comma_runon_word_count():
    runon = "a, " * 50
    result = orchestrator._first_sentences(runon)
    words = result.rstrip(".").replace(",", "").split()
    assert len(words) <= 45
    assert result.endswith(".")


def test_short_name_strips_indonesian_legal_wrapper():
    assert orchestrator._short_name("PT Nusantara Sample Sentosa Tbk") == "Nusantara Sample Sentosa"
    assert orchestrator._short_name("PT. Generic Sample Bank Tbk.") == "Generic Sample Bank"


def test_gaps_from_keeps_only_known_sections():
    verdict = "Quick Hits :: add X\nUnknown :: y\n- Deals & Movements :: funding round\nrandom line"
    gaps = orchestrator._gaps_from(verdict, {"Quick Hits", "Deals & Movements"})
    assert gaps == [("Quick Hits", "add X"), ("Deals & Movements", "funding round")]
