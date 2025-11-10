// DeckExportPanel.js
import React, { useState } from "react";
import { Save, Download,Link as LinkIcon } from "lucide-react";
import { patchPPTXLinks, buildDeckPpt, fetchArticleFullText } from "../api"
import { ClipLoader } from "react-spinners";

// Backend endpoint
const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";
const SLIDESGPT_API = `${API_BASE}/slidesgpt/generate`;


// Defensive link getter (add more fallbacks if needed)
const getArticleLink = (art) =>
  art.link ||
  art.url ||
  art.source_url ||
  art.source ||
  (art.meta_data?.link ?? "N/A");

function buildSourceUrlArray(articlesByCategory) {
  // Flatten the articles by category, preserve order as slides would appear.
  const all = [];
  Object.entries(articlesByCategory).forEach(([cat, articles]) => {
    articles.forEach((a) => {
      let url = getArticleLink(a);
      // Remove N/A or blank links for slides with no source
      all.push(url && url !== "N/A" ? url : "");
    });
  });
  return all;
}


async function fetchFullTextForArticles(selectedArticles) {
  return Promise.all(selectedArticles.map(async (article) => {
    const link = getArticleLink(article);
    if (!link || link === "N/A") {
      return { ...article, full_text: article.summary || "" };
    }
    try {
      const data = await fetchArticleFullText(link, article.summary || "");
      return {
        ...article,
        full_text: data.full_text || article.summary // fallback
      };
    } catch (e) {
      console.error("Error fetching full text for", article.title, e);
      return {
        ...article,
        full_text: article.summary || ""
      };
    }
  }));
}


// Prompt builder
function buildSlidesGPTPrompt(title, template, contentOptions, articlesByCategory) {
  let prompt = `Generate a PowerPoint titled "${title}" using the "${template}".\n\n`;
  if (contentOptions.includeSummary)
    prompt += "Include an executive summary slide summarizing key trends across all articles.\n";
  if (contentOptions.addCharts)
    prompt += "Add trend analysis charts if relevant.\n";
  prompt += `Generate a PowerPoint titled "Gen AI & LLM Trends - 2025" using the "Standard Research Template".

            Include an executive summary slide summarizing key trends across all articles.
            Add trend analysis charts if relevant.

            For each article below, generate one slide per article. For each slide, you MUST include these 4 elements:
            1. Main Slide Title: Create a concise, human-friendly title as the slide heading, based on the article's "Original Article Title"
            2. Subtitle: Display the "Original Article Title" as a subtitle on the slide
            3. Body Content: Use the provided "Summary" as the main body content on the slide, including all key data points, facts, statistics, organization and product names, and any important figures or trends mentioned in the summary. Do not omit any such details.
            4. Source Footer: **MANDATORY - Place the "Source" URL at the bottom of every slide as a footer. The source MUST be visible on the slide. Missing the source is an ERROR.**

            CRITICAL: Each slide MUST have all 4 elements above. The Source URL must appear at the bottom of EVERY content slide.

            Do not summarize, paraphrase, or omit any part of the provided Summary or Source.
            Do not generate your own content. Only use the provided fields.

            Organize the slides by the categories as shown below.

            `;
    
  Object.entries(articlesByCategory).forEach(([category, articles]) => {
    if (!articles.length) return;
    prompt += `## ${category}\n`;
    articles.forEach((art, idx) => {
      const curr_link = getArticleLink(art);
      const sanitizedSource = curr_link
        ? curr_link.replace(/^https?:\/\//, '').replace(/^www\./, '')
        : '';
      prompt += `Original Article Title: "${art.title}" [Score: ${art.score ?? art.relevance_score ?? '--'}]\n`;
      prompt += `Summary: ${art.full_text}\n`;
      if (sanitizedSource) {
        prompt += `Source: ${sanitizedSource}\n`;
      }
      prompt += "\n";
    });
  });
  return prompt;
}


const DeckExportPanel = ({ token, categories, selectedArticles }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [slidesgptLinks, setSlidesgptLinks] = useState(null);

  const [isPatching, setIsPatching] = useState(false);
  const [isBuildingLocal, setIsBuildingLocal] = useState(false);
  const [showEmbed, setShowEmbed] = useState(false);
  
  
  // Save enriched articles (used in slide order for URLs)
  const [enrichedArticles, setEnrichedArticles] = useState([]);

  const [localViewerUrl, setLocalViewerUrl] = useState(null);   // CHANGE: viewer URL for local PPT
  //const [showEmbed, setShowEmbed] = useState(false);          // CHANGE: toggle preview for both paths

  const [title, setTitle] = useState("Gen AI & LLM Trends - 2025");
  const [template, setTemplate] = useState("Standard Research Template");
  const [contentOptions, setContentOptions] = useState({
    includeSummary: true,
    generateSummaries: true,
    addCharts: true,
    sourceCitations: false,
  });

  // DEBUG: Print selectedArticles at every render
  console.log("[DeckExportPanel] selectedArticles:", selectedArticles);

  async function handleExportPPT() {
    setIsExporting(true);
    setSlidesgptLinks(null);
    setLocalViewerUrl(""); // CHANGE: clear local viewer when switching path

    console.log("selectedArticles passed to fetchFullTextForArticles:", selectedArticles);
    // Fetch full text for all selected articles FIRST!
    const enrichedArticles = await fetchFullTextForArticles(selectedArticles);
    console.log("enRICHED ARTICLES:", enrichedArticles);
    setEnrichedArticles(enrichedArticles); // Save for later URL extraction

    // Re-group by category using enriched articles
    const articlesByCategory = categories.reduce((acc, cat) => {
      acc[cat.name] = enrichedArticles.filter(a => (a.category || "") === cat.id);
      return acc;
    }, {});
    const prompt = buildSlidesGPTPrompt(title, template, contentOptions, articlesByCategory);
    
    console.log("[DeckExportPanel] SlidesGPT Prompt:\n", prompt);
    //const safePrompt = processPromptForAPI(prompt);
    //console.log("[DeckExportPanel] SAFE PROMPT SlidesGPT Prompt:\n", safePrompt);
    try {
      const res = await fetch(SLIDESGPT_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        //body: JSON.stringify({ prompt:trimPrompt(prompt,) }),
        body: JSON.stringify({ prompt:prompt }),
      });
      const data = await res.json();
      if (!data.id) throw new Error("SlidesGPT API failed!");

      setSlidesgptLinks({
        embed: data.embed,
        id: data.id
      });
      setShowEmbed(true); // CHANGE: auto-open preview if desired
    } catch (e) {
      alert("Export failed: " + (e?.message || "Unknown error"));
    }
    setIsExporting(false);
  }

  // PATCH & DOWNLOAD HANDLER
  async function handlePatchAndDownload() {
    if (!slidesgptLinks?.id) {
      alert("Please generate the PPT first!");
      return;
    }
    setIsPatching(true);
    // Use enrichedArticles for best accuracy, or fallback to selectedArticles
    const articles = enrichedArticles.length ? enrichedArticles : selectedArticles;
    // RE-GROUP BY CATEGORY (use same grouping as prompt for order!)
    const byCat = categories.reduce((acc, cat) => {
      acc[cat.name] = articles.filter(a => (a.category || "") === cat.id);
      return acc;
    }, {});
    const sourceUrlList = buildSourceUrlArray(byCat);

    try {
      const blob = await patchPPTXLinks(slidesgptLinks.id, sourceUrlList);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `presentation-${slidesgptLinks.id}-with-links.pptx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to patch links: " + err?.message);
    }
    setIsPatching(false);
  }

   // Local PPT builder (uses backend /deck/build-ppt?return_url=1)
  async function handleBuildDraftPptLocally() {
    if (!selectedArticles?.length) {
      alert("No articles selected.");
      return;
    }
    setIsBuildingLocal(true);
    setLocalViewerUrl(null); // CHANGE: reset preview
    setSlidesgptLinks(null); // CHANGE: clear SlidesGPT state when switching paths

    try {
      // ✅ NEW: Enrich FIRST (same as SlidesGPT path)
      const enriched = await fetchFullTextForArticles(selectedArticles); // ✅ NEW
      setEnrichedArticles(enriched); // ✅ NEW

// ✅ CHANGED: Build sections from *enriched* articles so we use full_text
      const sections = categories.map((cat) => ({
        category: cat.name,
        articles: enriched // ✅ CHANGED (was selectedArticles)
          .filter((a) => (a.category || "") === cat.id)
          .map((a) => ({
            main_title: a.title,
            original_title: a.title || "",
            summary: a.full_text || a.summary || "", // ✅ CHANGED (prefer full_text)
            source:
              a.link ||
              a?.meta_data?.link ||
              a.url ||
              a.source_url ||
              "",
          })),
      }));

      const payload = {
        title,
        subtitle: "Draft deck",
        include_summary: true,
        sections,
      };

      // Ask backend to return URLs so we can preview online
      const result = await buildDeckPpt(token, payload, { returnUrl: true });

      // Try to show preview if available (Office viewer or PDF)
      const previewUrl = result?.viewer_url || result?.pdf_abs_url;
      if (previewUrl) {
        setLocalViewerUrl(previewUrl);
        setShowEmbed(true);
      }

      // Always download the file as well, since preview might not work
      if (result?.absolute_file_url || result?.file_url) {
        const downloadUrl = result.absolute_file_url || result.file_url;
        // If relative URL, prepend API base
        const fullUrl = downloadUrl.startsWith('http')
          ? downloadUrl
          : `${API_BASE}${downloadUrl}`;

        // Trigger download
        const a = document.createElement("a");
        a.href = fullUrl;
        a.download = `${payload.title.replace(/\s+/g, "_")}.pptx`;
        document.body.appendChild(a);
        a.click();
        a.remove();

        if (!previewUrl) {
          alert("PPT generated and downloaded successfully! (Preview not available without HTTPS)");
        }
      } else if (result instanceof Blob) {
        // Fallback: if backend returned a blob directly
        const url = window.URL.createObjectURL(result);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${payload.title.replace(/\s+/g, "_")}.pptx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (e) {
      alert("Failed to build PPT: " + (e?.message || "Unknown error"));
      console.error(e);
    } finally {
      setIsBuildingLocal(false);
    }
  }

  // --- UI ---
  // UI
  return (
    <div className="bg-white rounded-lg shadow p-6 mt-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Generate Deck</h3>

        {/* CHANGE: show BOTH primary actions always */}
        <div className="flex items-center gap-3">
          <button
            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 flex items-center gap-2 disabled:opacity-50"
            onClick={handleBuildDraftPptLocally}
            disabled={isBuildingLocal}
            title="Generate PPT locally on your server"
          >
            {isBuildingLocal ? (
              <ClipLoader color="#fff" size={18} className="mr-2" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {isBuildingLocal ? "Building..." : "Build PPT (Local)"}
          </button>

          <button
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
            onClick={handleExportPPT}
            disabled={isExporting}
            title="Generate PPT via SlidesGPT (external)"
          >
            {isExporting ? (
              <ClipLoader color="#fff" size={18} className="mr-2" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {isExporting ? "Generating..." : "Export PPT (SlidesGPT)"}
          </button>
        </div>
      </div>

      {/* Settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-2">Deck Settings</h4>
          <div className="space-y-3">
            <div>
              <label className="text-sm text-gray-600">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">Template</label>
              <select
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option>Standard Research Template</option>
                <option>Executive Summary Template</option>
                <option>Detailed Analysis Template</option>
              </select>
            </div>
          </div>
        </div>

        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-2">Content Options</h4>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={contentOptions.includeSummary}
                onChange={(e) =>
                  setContentOptions({ ...contentOptions, includeSummary: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm">Include executive summary</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={contentOptions.generateSummaries}
                onChange={(e) =>
                  setContentOptions({ ...contentOptions, generateSummaries: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm">Generate article summaries</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={contentOptions.addCharts}
                onChange={(e) =>
                  setContentOptions({ ...contentOptions, addCharts: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm">Add trend analysis charts</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={contentOptions.sourceCitations}
                onChange={(e) =>
                  setContentOptions({ ...contentOptions, sourceCitations: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm">Include source citations</span>
            </label>
          </div>
        </div>
      </div>

      {/* CHANGE: Secondary actions and preview that work for BOTH paths */}
      <div className="mt-6 space-y-4">
        {/* SlidesGPT-only extra action */}
        {slidesgptLinks && (
          <button
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
            onClick={handlePatchAndDownload}
            disabled={isPatching}
          >
            {isPatching ? (
              <ClipLoader color="#fff" size={18} className="mr-2" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {isPatching ? "Preparing..." : "Patch Links & Download"}
          </button>
        )}

        {/* One toggle button that works for both SlidesGPT + local viewer */}
        {(slidesgptLinks?.embed || localViewerUrl) && (
          <button
            className="px-4 py-2 border border-gray-300 rounded-lg flex items-center gap-2"
            onClick={() => setShowEmbed((v) => !v)}
          >
            <Save className="w-4 h-4" />
            {showEmbed ? "Hide Online Preview" : "Show in PowerPoint Online"}
          </button>
        )}

        {/* Iframe preview — either SlidesGPT embed OR local Office viewer */}
        {showEmbed && (slidesgptLinks?.embed || localViewerUrl) && (
          <>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <LinkIcon className="w-4 h-4" />
              <span>Showing in PowerPoint Online ({slidesgptLinks?.embed ? "SlidesGPT" : "Local"}).</span>
            </div>
            <div className="my-4">
              <iframe
                src={slidesgptLinks?.embed || localViewerUrl}
                style={{
                  width: "100%",
                  minHeight: "600px",
                  border: "1px solid #eee",
                  borderRadius: "10px",
                }}
                allowFullScreen
                title="PowerPoint Online Preview"
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DeckExportPanel;