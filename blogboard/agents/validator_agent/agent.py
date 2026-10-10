import json
import re
from datetime import datetime
from blogboard.graph.state import BlogState
from blogboard.services.llm import LLMAgentService
from blogboard.services.storage import R2StorageService
from blogboard.config.settings import app_settings
from blogboard.services.prompt_manager import prompt_manager
from .prompts import VALIDATOR_PROMPT


MAX_REVISIONS = 3


def validator_node(state: BlogState) -> BlogState:
    print("  => [ValidatorAgent] Running...")
    
    if state.get("dry_run"):
        print("  [DRY RUN] Simulating Approval and Metadata Gen.")
        return {
            **state, 
            "revision_needed": False,
            "title": "Dry Run Generated Title",
            "slug": "dry-run-generated",
            "md_path": "r2://dry-run",
            "description": "Dry run generic description.",
        }

    current_revision = state.get("revision_count", 0)
    topic = state.get("topic", "")
    content = state.get("content", "")
    domain = state.get("domain", "")
    date = state.get("date", datetime.now().strftime("%Y-%m-%d"))
    if domain not in app_settings.tags.model_dump():
        raise ValueError(f"Unknown article category: {domain!r}")

    prompt = prompt_manager.get_prompt(
        prompt_name="Validator_Prompt",
        fallback_prompt=VALIDATOR_PROMPT,
        topic=topic,
        content=content
    )
    
    llm_service = LLMAgentService(temperature=0.1) 
    res = llm_service.llm.invoke(prompt)
    
    raw = res.content.strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError("Validator returned invalid JSON; refusing to publish.") from e
    if not isinstance(data, dict) or not isinstance(data.get("approved"), bool):
        raise ValueError("Validator response must be an object with a boolean 'approved' field.")

    approved = data["approved"]
    feedback = data.get("feedback", "")
    if not isinstance(feedback, str):
        raise ValueError("Validator feedback must be a string.")

    if not approved and current_revision >= MAX_REVISIONS:
        raise RuntimeError(
            f"Article was rejected after {MAX_REVISIONS} revisions; refusing to publish."
        )

    revision_needed = not approved
    
    if revision_needed:
        print(f"  [AGENT] Draft REJECTED. Feedback: {feedback}")
        return {
            **state,
            "revision_needed": True,
            "validator_feedback": feedback,
            "revision_count": current_revision + 1
        }
        
    print(f"  [AGENT] Draft APPROVED! Generating Metadata and Saving to R2...")
    
    # Save to R2
    title = data.get("title")
    description = data.get("description")
    proposed_slug = data.get("slug")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Approved validator response must include a non-empty title.")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Approved validator response must include a non-empty description.")
    if not isinstance(proposed_slug, str) or not proposed_slug.strip():
        raise ValueError("Approved validator response must include a non-empty slug.")

    slug_value = re.sub(r"[^a-z0-9]+", "-", proposed_slug.lower()).strip("-")
    if not slug_value:
        raise ValueError("Validator slug does not contain any URL-safe characters.")
    md_relative = f"blogs/{domain}/{slug_value}.md"
    storage = R2StorageService()
    
    if not storage.put_object(md_relative, content, content_type="text/markdown"):
        raise RuntimeError(f"Failed to upload article Markdown to R2: {md_relative}")
    articles = storage.get_articles_json(domain)
    articles = [a for a in articles if a.get("id") != md_relative]
    
    articles.append({
        "id": md_relative,
        "category": domain,
        "topic": topic,
        "subtopics": state.get("subtopics", ""),
        "title": title,
        "description": description,
        "date": date,
        "tags": [domain],
        "readTime": state.get("read_time", "5 min"),
        "file": md_relative,
    })
    
    articles = sorted(articles, key=lambda x: x["date"], reverse=True)
    if not storage.save_articles_json(domain, articles):
        raise RuntimeError(f"Failed to update the R2 article index for category {domain!r}.")
    
    return {
        **state,
        "revision_needed": False,
        "title": title,
        "description": description,
        "slug": slug_value,
        "md_path": f"r2://{md_relative}"
    }
