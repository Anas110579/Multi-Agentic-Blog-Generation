# BlogBoard

BlogBoard generates technical Machine Learning and AI articles with LangGraph and Groq, validates drafts, and publishes Markdown and article indexes to Cloudflare R2. The static website in `blogboard/web` reads those published files from R2.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Cloudflare R2 credentials and a public bucket URL for live publishing
- A Groq API key; Tavily and Guardian API keys are needed for AI-news publishing

## Local setup

```powershell
uv sync
Copy-Item .env.example .env
```

Fill in the values in `.env`. Empty credentials are allowed for dry runs, but live publishing requires the relevant API keys and R2 credentials.

Preview a run without making network calls or writing files:

```powershell
uv run multi-agentic-blog-generation --dry-run --scheduled
```

Run the category assigned to a particular date:

```powershell
uv run multi-agentic-blog-generation --date 2026-10-12 --scheduled
```

Run a specific category or AI-news generation explicitly:

```powershell
uv run multi-agentic-blog-generation --domain ml
uv run multi-agentic-blog-generation --ainews
```

Without `--scheduled`, `--domain`, or `--ainews`, tutorial generation selects a category based on publication history.

## Publishing schedule

The weekly schedule is Monday–Sunday: `ml`, `dl`, `statistics`, `nlp`, `cv`, `genai`, `ainews`. GitHub Actions runs the scheduled publisher daily at 02:30 UTC (08:00 IST). GitHub scheduled workflows may be delayed.

## GitHub Actions configuration

Add these repository **Actions secrets** before enabling live generation:

| Secret | Used for |
| --- | --- |
| `GROQ_API_KEY` | Groq article generation and validation |
| `R2_ACCOUNT_ID` | Cloudflare R2 endpoint |
| `R2_ACCESS_KEY_ID` | R2 writes |
| `R2_SECRET_ACCESS_KEY` | R2 writes |
| `R2_BUCKET_NAME` | Destination bucket |
| `TAVILY_API_KEY` | AI-news research |
| `GUARDIAN_API_KEY` | AI-news research |

The GitHub Pages workflow also needs the repository **Actions variable** `R2_PUBLIC_URL` set to the public base URL of the R2 bucket (for example, `https://<bucket>.r2.dev`). Enable GitHub Pages with **GitHub Actions** as the build and deployment source. Configure the R2 bucket's CORS policy to allow browser reads from the published Pages origin.

Use the `Generate and publish article` workflow's manual dispatch to test publishing. The optional date input is interpreted in IST and selects that date's scheduled category.

## Tests

```powershell
uv run pytest
```
