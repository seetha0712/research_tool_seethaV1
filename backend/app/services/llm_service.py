import openai
from openai import OpenAI
import time
from app.core.config import OPENAI_API_KEY
import logging
from app.core.config import CATEGORY_OPTIONS
logger = logging.getLogger(__name__)


client = OpenAI(api_key=OPENAI_API_KEY)

# --- 1. Key Insights for Article Summary/Content ---
def key_insights(text: str) -> list:
    """
    Extract 1 concise, actionable, non-generic insight from the text for AI/business leaders.
    """
    prompt = (
        "From the text below, extract the single most important, non-generic, and actionable insight for AI or business leaders. "
        "Write it as one short sentence only, avoiding buzzwords or repetition. "
        "Format: 1. <insight>\n\n"
        f"Text:\n{text}"
    )
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                #model="gpt-3.5-turbo",
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a researcher who generates insights for Senior Leaders."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0
            )
            result = response.choices[0].message.content.strip()
            # Parse lines starting with "1. ", "2. "
            insight = ""
            for line in result.splitlines():
                line = line.strip()
                if line.startswith("1. "):
                    insight = line[3:].strip()
                    break
                elif line:
                    insight = line
                    break
            return [insight] if insight else []
        except Exception as e:
            if attempt == 2:
                logger.warning(f"OpenAI key_insights failed: {e}")
                return []
            time.sleep(1 + 2 * attempt)

# --- 2. Deep Insights for Full Article (on demand) ---
def deep_insights_from_content(content: str) -> dict:
    """
    Given scraped article content, generate a summary (2-3 sentences) and 2 actionable takeaways.
    """
    prompt = (
        "Given the article content below, respond in exactly the following format:\n"
        "\n"
        "1. First, write a concise summary of the article in 2-4 plain sentences. Ensure your summary includes all key data points, facts, statistics, organization and product names, and any important figures or trends mentioned in the article. Do NOT number, bullet, or prefix this summary—just write the summary as plain sentences. Do not add any section headings or extra explanation.\n"
        "2. Then, write exactly TWO actionable takeaways for financial leaders. Each takeaway should start with '1.' and '2.' on its own line. Do not add any extra text or commentary.\n"
        "\n"
        "Begin your response immediately with the summary, followed by the two actionable takeaways on separate lines.\n\n"
        f"Article:\n{content}"
   )
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                #model="gpt-3.5-turbo",
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a business analyst for financial leaders."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                temperature=0.3,
            )
            msg = response.choices[0].message.content.strip()
            # --- DEBUG: Always log/show what the LLM gave us ---
            logger.info(f"[DeepInsights LLM Raw Output]\n{msg}")

             # Split on lines starting with "1."
            lines = msg.splitlines()
            summary_lines = []
            takeaways = []
            for line in lines:
                if line.strip().startswith("1."):
                    # take all lines from here as takeaways
                    takeaways = [l[3:].strip() for l in lines if l.strip().startswith("1.") or l.strip().startswith("2.")]
                    break
                summary_lines.append(line)
            summary = " ".join(summary_lines).strip()
            if not summary:
                summary = "No summary available."
            return {"summary": summary, "takeaways": takeaways[:2]}
        
        except Exception as e:
            if attempt == 2:
                logger.warning(f"OpenAI deep_insights_from_content failed: {e}")
                return {"summary": "No summary available.", "takeaways": []}
            time.sleep(1 + 2 * attempt)


# --- 3. (Optional) Relevance & Category - if you still need these downstream ---
def score_article(text: str) -> int:
    prompt = (
    "You are a senior research analyst at a global financial institution (e.g., JPMorgan, Morgan Stanley).\n"
    "You must score the following article (0 to 100) for its value and actionable insight to senior financial or technology leaders (CIO, CTO, CEO, Heads of Digital, Wealth, Investment, or IT).\n"
    "\n"
    "SCORING RULES:\n"
    "- Assign a HIGH score (80–100) **if the article provides ANY of the following**:\n"
    "    • Strategic, actionable, or in-depth insights for leaders in banking, investment, wealth/asset management, or institutional finance—especially about AI, GenAI, LLMs, agentic AI, security, governance, or digital transformation.\n"
    "    • Practical recommendations or frameworks for decision-making, operations, or tech strategy in enterprise/financial services—even if NO specific companies are named.\n"
    "    • Analysis of emerging tech (e.g., MCP, A2A protocols, agentic AI, enterprise security/governance, interoperability) with clear implications for business/IT leadership.\n"
    "- Assign a MODERATE score (40–79) for general tech, AI/LLM news, or trends that might be useful for senior financial/IT leaders, but are less direct, less actionable, or generic.\n"
    "- Assign a LOW score (0–39) ONLY if the article is irrelevant, speculative, consumer-focused, or provides little to no value for enterprise, financial, or technology leaders.\n"
    "\n"
    "TIPS:\n"
    "- REWARD any article that helps senior leaders (CIO, CTO, CEO, Head of Digital/IT/Wealth) understand, adopt, or respond to technology, governance, operational, or competitive challenges in large organizations—even if it is conceptual or about enabling frameworks/protocols.\n"
    "- DO NOT give high scores to content that is purely generic, speculative, or irrelevant to enterprise/finance/tech leadership.\n"
    "- If in doubt, score **higher** for insightful, practical, or strategic content that enterprise financial/technology leaders would value, and **lower** only for clearly generic or non-actionable news.\n"
    "\n"
    "Return ONLY a single number (0 to 100) as the score. Do NOT provide explanations.\n"
    f"\nArticle:\n{text[:3000]}"
)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                #model="gpt-3.5-turbo",
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Strict relevance grader for banking, investment, and wealth management executives."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0
            )
            msg = response.choices[0].message.content.strip()
            digits = ''.join(filter(str.isdigit, msg))
            score = int(digits) if digits else 0
            return min(max(score, 0), 100)
        except Exception as e:
            if attempt == 2:
                return 0
            time.sleep(1 + 2 * attempt)

from difflib import get_close_matches
from app.core.config import CATEGORY_OPTIONS

def categorize_article(text: str, category_options=None) -> str:
    """
    Classify an article into exactly one of CATEGORY_OPTIONS.
    - Strong, rule-based prompt with category descriptions + few-shot examples
    - Strict single-label output (post-processed)
    - Robust normalization + fuzzy matching to avoid drift
    - Fallback to 'Uncategorized'
    """
    if not category_options:
        category_options = CATEGORY_OPTIONS

    # --- Descriptions to reduce ambiguity ---
    options_with_desc = {
        "AI & GenAI Trends": "Industry-wide trends, adoption, regulation, macro outlook.",
        "AI in Financial Institutions": "Banking, wealth/asset mgmt, insurance use cases, programs.",
        "Leading AI Innovators": "Company profiles/updates (OpenAI, Google, Anthropic, Meta, etc.).",
        "Agentic AI": "Autonomous/agentic systems, orchestration, multi-agent, tool-use.",
        "Broader AI Topics": "AI research, ethics, policy, general AI topics beyond agents.",
        "Tech Corner": "Engineering, architectures, APIs, SDKs, developer-focused how-tos.",
        "AI Beyond Finance": "AI in other industries (healthcare, retail, manufacturing, etc.).",
        "Uncategorized": "Doesn’t clearly fit any above category."
    }

    # Build labeled list (only for categories that exist in options)
    labeled_list = "\n".join(
        f"- {c}: {options_with_desc.get(c, '')}".strip()
        for c in category_options
    )

    # --- Few-shot examples (short + varied) ---
    few_shots = [
        {
            "title": "Morgan Stanley expands GenAI copilots for financial advisors",
            "category": "AI in Financial Institutions",
        },
        {
            "title": "OpenAI unveils new multimodal roadmap and enterprise controls",
            "category": "Leading AI Innovators",
        },
        {
            "title": "Multi-agent planning improves tool-use reliability",
            "category": "Agentic AI",
        },
        {
            "title": "EU AI Act: what it means for enterprises",
            "category": "AI & GenAI Trends",
        },
        {
            "title": "Streaming vector DB patterns for RAG at scale",
            "category": "Tech Corner",
        },
        {
            "title": "AI cuts hospital readmissions by 12%",
            "category": "AI Beyond Finance",
        },
    ]

    examples_str = "\n".join(
        f'Title: "{ex["title"]}"\nCategory: {ex["category"]}\n'
        for ex in few_shots
        if ex["category"] in category_options  # include only valid labels
    )

    # --- Prompt ---
    prompt = f"""
You are an expert AI content classifier.

TASK
- Choose EXACTLY ONE category from the list.
- Respond with ONLY the category name (must match one from the list).
- If unsure, respond with "Uncategorized".
- If multiple seem plausible, pick the MOST RELEVANT primary theme.

CATEGORIES
{labeled_list}

EXAMPLES
{examples_str}

ARTICLE (trimmed):
{text[:3000]}
"""

    # Call LLM with retries
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Classify into exactly one category."},
                    {"role": "user", "content": prompt.strip()},
                ],
                max_tokens=15,
                temperature=0,
            )
            raw = (response.choices[0].message.content or "").strip()

            # --- Post-process: normalize + exact/fuzzy map to allowed options ---
            norm = raw.strip().strip('"').strip("'")
            # Exact case-insensitive match
            for opt in category_options:
                if opt.lower() == norm.lower():
                    return opt

            # Fuzzy fallback (helps if model replies e.g., 'AI & Gen AI Trends')
            best = get_close_matches(norm, category_options, n=1, cutoff=0.75)
            if best:
                return best[0]

            # If the model replied like: "Category: XYZ"
            if ":" in norm:
                tail = norm.split(":", 1)[1].strip()
                for opt in category_options:
                    if opt.lower() == tail.lower():
                        return opt
                best = get_close_matches(tail, category_options, n=1, cutoff=0.75)
                if best:
                    return best[0]

            # Last resort
            return "Uncategorized" if "Uncategorized" in category_options else category_options[-1]

        except Exception as e:
            if attempt == 2:
                # On persistent failure, safely fallback
                return "Uncategorized" if "Uncategorized" in category_options else category_options[-1]
            time.sleep(1 + 2 * attempt)

def summarize_article(text: str, model="gpt-4o", max_tokens=150) -> str:
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Summarize this article in 3 sentences."},
                    {"role": "user", "content": text[:3000]}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == 2:
                logger.warning(f"OpenAI summarization failed: {e}")
                return text[:500]
            time.sleep(1 + 2 * attempt)