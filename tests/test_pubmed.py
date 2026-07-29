import asyncio
from xml.etree import ElementTree as ET

import pytest

from src.retrieval.pubmed_retriever import PubMedRetrievalError, PubMedRetriever


def test_pubmed_article_parser_handles_multiple_abstract_sections():
    element = ET.fromstring(
        """
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345</PMID>
            <Article>
              <ArticleTitle>Test <i>medical</i> title</ArticleTitle>
              <Abstract>
                <AbstractText>Background text.</AbstractText>
                <AbstractText>Conclusion text.</AbstractText>
              </Abstract>
              <AuthorList>
                <Author><LastName>Wang</LastName><ForeName>Ze</ForeName></Author>
              </AuthorList>
              <Journal>
                <Title>Medical Journal</Title>
                <JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue>
              </Journal>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
    )
    article = PubMedRetriever._parse_article(element)
    assert article is not None
    assert article["pmid"] == "12345"
    assert article["title"] == "Test medical title"
    assert "Background text." in article["content"]
    assert "Conclusion text." in article["content"]
    assert article["authors"] == ["Ze Wang"]


def test_pubmed_transport_failure_is_not_reported_as_no_results():
    async def scenario():
        retriever = PubMedRetriever()

        async def fail_search(query, max_results):
            raise asyncio.TimeoutError

        retriever._search_pubmed = fail_search
        try:
            with pytest.raises(PubMedRetrievalError, match="unavailable"):
                await retriever.search("diabetes")
        finally:
            await retriever.close()

    asyncio.run(scenario())
