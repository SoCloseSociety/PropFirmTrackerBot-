"""
PropFirmTracker Bot - AI Summarizer
=====================================
Uses Claude Haiku to generate trader-friendly summaries of changes.
Optimized for minimal token usage to keep costs ultra low.
"""

import requests
from utils.logger import log_info, log_error, log_debug
from config import ANTHROPIC_API_KEY, AI_MODEL, AI_MAX_TOKENS


class AISummarizer:
    """Generates AI-powered summaries of prop firm changes."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self):
        self.enabled = ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_ANTHROPIC_KEY_HERE"
        if not self.enabled:
            log_info("AI Summarizer disabled — no API key configured", tag="AI")

    def summarize_change(self, firm_name, page_type, content_snippet):
        """Generate a short, trader-focused summary of a detected change."""
        if not self.enabled:
            return f"Change detected on {firm_name} ({page_type}). Check their website for details."

        prompt = f"""You are a prop firm analyst bot. A change was detected on {firm_name}'s {page_type} page.

Here's the current page content (snippet):
---
{content_snippet[:1500]}
---

Write a 2-3 sentence summary for traders. Focus on:
- What changed (pricing, rules, drawdown limits, profit targets, etc.)
- How it impacts traders (positive/negative)
- Any action they should take

Be concise and direct. Use trader language. No fluff."""

        return self._call_api(prompt)

    def analyze_scam_report(self, firm_name, report_text, source):
        """Analyze a potential scam report and generate severity assessment."""
        if not self.enabled:
            return f"Potential issue reported for {firm_name}. Source: {source}"

        prompt = f"""You are a prop firm risk analyst. Analyze this report about {firm_name}:

Report: {report_text[:800]}
Source: {source}

In 2-3 sentences:
1. Summarize the concern
2. Rate credibility (low/medium/high) based on specificity
3. Recommend action for traders (wait, investigate, or avoid)

Be balanced — don't amplify fear without evidence."""

        return self._call_api(prompt)

    def generate_comparison(self, firm1_data, firm2_data):
        """Generate a brief comparison between two firms."""
        if not self.enabled:
            return "AI comparison unavailable. Check firm websites directly."

        prompt = f"""Compare these two prop firms briefly for traders:

Firm 1: {firm1_data}
Firm 2: {firm2_data}

In 4-5 bullet points, compare: account sizes, pricing, profit split, drawdown rules, and Trustpilot score. Be objective."""

        return self._call_api(prompt)

    def _call_api(self, prompt):
        """Make API call to Claude with minimal tokens."""
        try:
            headers = {
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            data = {
                "model": AI_MODEL,
                "max_tokens": AI_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = requests.post(self.API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block["text"]

            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            log_debug(f"AI call: {input_tokens} in / {output_tokens} out tokens", tag="AI")

            return text.strip()

        except Exception as e:
            log_error(f"AI API error: {e}", tag="AI")
            return "AI analysis temporarily unavailable."
