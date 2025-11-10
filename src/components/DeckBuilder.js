import React from "react";
import { X, Link as LinkIcon, Mail } from "lucide-react";
import DeckExportPanel from "./DeckExportPanel";
import { updatePaidArticle,updateArticleStatus } from "../api";

// Helper: "best" link/id for matching
const getArticleLink = (art) =>
  art.link ||
  art.url ||
  art.source_url ||
  (art.meta_data?.link ?? null);

const DeckBuilder = ({
  token,
  categories,
  selectedArticles,
  setSelectedArticles,
  removedFromDeck,
  setRemovedFromDeck
}) => {
  // Email sharing handler
  const handleEmailShare = () => {
    if (selectedArticles.length === 0) {
      alert("No articles selected to share");
      return;
    }

    // Group articles by category
    const articlesByCategory = categories.map(category => {
      const categoryArticles = selectedArticles.filter(a => a.category === category.id);
      return { category, articles: categoryArticles };
    }).filter(group => group.articles.length > 0);

    // Build HTML email body with proper formatting
    let emailBody = "GenAI Research Monthly Summary\n";
    emailBody += "=".repeat(60) + "\n\n";
    emailBody += `Total Articles: ${selectedArticles.length}\n`;
    emailBody += `Generated: ${new Date().toLocaleDateString()}\n\n`;

    articlesByCategory.forEach(({ category, articles }, catIdx) => {
      emailBody += `\n${"━".repeat(60)}\n`;
      emailBody += `${catIdx + 1}. ${category.name.toUpperCase()}\n`;
      emailBody += `${"━".repeat(60)}\n\n`;

      articles.forEach((article, idx) => {
        const url = article.link || article.meta_data?.link || "";
        const score = article.score ?? article.relevance_score ?? "N/A";
        const source = article.source?.name || article.source_name || article.source || "Unknown";

        emailBody += `${idx + 1}. ${article.title}\n`;
        emailBody += `   Source: ${source} | Score: ${score}\n`;

        if (article.summary) {
          const summaryText = article.summary.substring(0, 200);
          emailBody += `   Summary: ${summaryText}${article.summary.length > 200 ? "..." : ""}\n`;
        }

        // Put URL on its own line for email clients to auto-link
        if (url) {
          emailBody += `   🔗 ${url}\n`;
        }

        emailBody += `\n`;
      });
    });

    emailBody += `\n${"=".repeat(60)}\n`;
    emailBody += `End of Summary\n`;

    // Create mailto link
    const subject = encodeURIComponent("GenAI Research Monthly Summary - " + new Date().toLocaleDateString());
    const body = encodeURIComponent(emailBody);
    const mailtoLink = `mailto:?subject=${subject}&body=${body}`;

    // Open default email client
    window.location.href = mailtoLink;
  };

  // Async handler to remove article and update backend
  const handleRemoveArticle = async (article) => {
  const link = getArticleLink(article);
  const id = article.id;
  const isPaid =
    article?.is_paid ??
    (!!article.source && !/^https?:\/\//.test(article.source)); // fallback heuristic
  console.log("[REMOVE] Attempting to remove:", { id, link, article });
  try {
    
    if (isPaid) {
      // Paid route
      await updatePaidArticle(token, id, { status: "shortlisted" });
    } else {
      // Regular article route
      await updateArticleStatus(id, "shortlisted", token);
    }


    //await updatePaidArticle(token, id, { status: "shortlisted" });
    setRemovedFromDeck(prev => [
      ...prev,
      ...(id ? [id] : []),
      ...(link ? [link] : []),
    ]);
    // Debug: Show removedFromDeck after update
    setTimeout(() => {
      console.log("[REMOVE] removedFromDeck after removal:", removedFromDeck);
    }, 0);
  } catch (e) {
    alert("Failed to update article status. Please try again.");
    console.error(e);
  }
};

  return (
    <div className="p-6 space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Monthly Deck Structure</h3>
          <button
            onClick={handleEmailShare}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            disabled={selectedArticles.length === 0}
            title="Share summary via email"
          >
            <Mail className="w-4 h-4" />
            Share via Email
          </button>
        </div>
        <div className="space-y-4">
          {categories.map((category) => {
            const categoryArticles = selectedArticles.filter(a => a.category === category.id);
            const Icon = category.icon;
            return (
              <div key={category.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-blue-500" />
                    <h4 className="font-medium">{category.name}</h4>
                  </div>
                  <span className="text-sm text-gray-500">{categoryArticles.length} articles</span>
                </div>
                {categoryArticles.length > 0 ? (
                  <div className="space-y-2">
                    {categoryArticles.map(article => {
                      const isPaid = !!article.source && !/^https?:\/\//.test(article.source);
                      const url = article.link || article.meta_data?.link;
                      const score = article.score ?? article.relevance_score ?? "--";
                      return (
                        <div
                          key={article.id || article.link}
                          className="flex flex-col md:flex-row md:items-center justify-between p-3 bg-gray-50 rounded mb-2"
                        >
                          <div className="flex-1">
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-sm text-blue-700 hover:underline flex items-center gap-1"
                            >
                              {article.title}
                              <LinkIcon className="w-3 h-3 ml-1 text-blue-500 inline" />
                            </a>
                            <p className="text-xs text-gray-500 mt-0.5">
                              Source:{" "}
                              {isPaid ? (
                                <>{article.source} &nbsp;|&nbsp;
                                  <a href={url} className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">{url}</a>
                                </>
                              ) : (
                                <a href={url} className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">{url}</a>
                              )}
                              &nbsp; | Score: <span className="font-semibold">{score}</span>
                            </p>
                            {article.summary && (
                              <p className="text-xs text-gray-700 mt-1">{article.summary}</p>
                            )}
                          </div>
                          <div className="flex-shrink-0 mt-2 md:mt-0 md:ml-3">
                            <button
                              onClick={() => handleRemoveArticle(article)}
                              className="text-red-600 hover:bg-red-50 p-1 rounded"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No articles selected for this category</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {/* Deck Export Panel */}
      <DeckExportPanel
        token={token} 
        categories={categories}
        selectedArticles={selectedArticles}
      />
    </div>
  );
};

export default DeckBuilder;