"""Tests for imslp_agent module."""

import pytest
from modules.imslp_agent import (
    detect_era,
    _extract_page_metadata,
    _extract_pdf_links,
)


class TestDetectEra:
    def test_year_based_baroque(self):
        assert detect_era("", year=1700) == "baroque"

    def test_year_based_classical(self):
        assert detect_era("", year=1790) == "classical"

    def test_year_based_romantic(self):
        assert detect_era("", year=1870) == "romantic"

    def test_year_based_modern(self):
        assert detect_era("", year=1950) == "modern"

    def test_year_boundary_baroque_classical(self):
        assert detect_era("", year=1749) == "baroque"
        assert detect_era("", year=1750) == "classical"

    def test_composer_bach(self):
        assert detect_era("Johann Sebastian Bach", year=None) == "baroque"

    def test_composer_mozart(self):
        assert detect_era("Wolfgang Amadeus Mozart", year=None) == "classical"

    def test_composer_beethoven(self):
        assert detect_era("Ludwig van Beethoven", year=None) == "classical"

    def test_composer_chopin(self):
        assert detect_era("Frédéric Chopin", year=None) == "romantic"

    def test_composer_brahms(self):
        assert detect_era("Johannes Brahms", year=None) == "romantic"

    def test_unknown_composer_defaults_modern(self):
        assert detect_era("Unknown Composer", year=None) == "modern"

    def test_year_takes_priority_over_name(self):
        # Even though "Bach" is in the name, an explicit year wins
        assert detect_era("Carl Philipp Emanuel Bach", year=1950) == "modern"


class TestExtractPageMetadata:
    def _make_html(self, heading: str, content: str) -> str:
        return f"""
        <html><body>
        <h1 class="firstHeading">{heading}</h1>
        <div class="mw-parser-output"><p>{content}</p></div>
        </body></html>
        """

    def test_extracts_composer_from_title_parentheses(self):
        html = self._make_html("Symphony No. 5 (Beethoven, Ludwig van)", "A famous symphony.")
        composer, _ = _extract_page_metadata(html)
        assert "Beethoven" in composer

    def test_extracts_description_first_paragraph(self):
        html = self._make_html("Some Work (Some Composer)", "This is a detailed description of the work spanning multiple words.")
        _, desc = _extract_page_metadata(html)
        assert "detailed description" in desc

    def test_description_truncated_to_300_chars(self):
        long_text = "A" * 500
        html = self._make_html("Work (Composer)", long_text)
        _, desc = _extract_page_metadata(html)
        assert len(desc) <= 300

    def test_composer_infobox_row_preferred(self):
        html = """
        <html><body>
        <h1 class="firstHeading">Symphony No. 9 (Beethoven)</h1>
        <table><tr><th>Composer</th><td>Ludwig van Beethoven</td></tr></table>
        <div class="mw-parser-output"><p>Description here.</p></div>
        </body></html>
        """
        composer, _ = _extract_page_metadata(html)
        assert composer == "Ludwig van Beethoven"

    def test_empty_html_returns_empty_strings(self):
        composer, desc = _extract_page_metadata("<html><body></body></html>")
        assert composer == ""
        assert desc == ""


class TestExtractPdfLinks:
    def test_finds_direct_pdf_links(self):
        html = '<html><body><a href="/files/score.pdf">Download</a></body></html>'
        links = _extract_pdf_links(html, "https://imslp.org/wiki/Score", None)
        assert any("score.pdf" in l for l in links)

    def test_finds_disclaimer_links(self):
        html = '<html><body><a href="/wiki/Special:IMSLPDisclaimerAccept/12345">Download</a></body></html>'
        links = _extract_pdf_links(html, "https://imslp.org/wiki/Score", None)
        assert any("IMSLPDisclaimerAccept" in l for l in links)

    def test_finds_file_table_row_links(self):
        html = """
        <html><body>
        <table><tr class="we_have_file">
          <td><a href="/wiki/Special:IMSLPDisclaimerAccept/99999">Score PDF</a></td>
        </tr></table>
        </body></html>
        """
        links = _extract_pdf_links(html, "https://imslp.org/wiki/Score", None)
        assert any("99999" in l for l in links)

    def test_deduplicates_links(self):
        html = """
        <html><body>
        <a href="/files/score.pdf">Link 1</a>
        <a href="/files/score.pdf">Link 2</a>
        </body></html>
        """
        links = _extract_pdf_links(html, "https://imslp.org", None)
        assert links.count(next(l for l in links if "score.pdf" in l)) == 1

    def test_limits_to_five_results(self):
        hrefs = "\n".join(
            f'<a href="/files/score{i}.pdf">Link {i}</a>' for i in range(10)
        )
        html = f"<html><body>{hrefs}</body></html>"
        links = _extract_pdf_links(html, "https://imslp.org", None)
        assert len(links) <= 5
