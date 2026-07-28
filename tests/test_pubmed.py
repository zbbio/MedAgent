from xml.etree import ElementTree as ET

from src.retrieval.pubmed_retriever import PubMedRetriever


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
