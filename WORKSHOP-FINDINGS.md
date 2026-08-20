# Workshop Lab Findings — Prompt for Updating Instructions

You are an instructional designer helping update a hands-on workshop guide (`index.html`) for building an AI agent with IBM Bob and watsonx Orchestrate. Below are findings from a live test run of the lab. Update the instructions so that future attendees do not hit these issues.

---

## Finding 1 — Python tools do not execute on ITZ SaaS instances

**What happened:**
After successfully importing all three Python tools (`estimate_event_budget`, `suggest_venues`, `update_guest_list`) using `orchestrate tools import -k python`, the agent would respond to every tool-calling message with:

> "I have encountered an error calling the tool. Please try again. Error Details: Error getting Python tool status."

The agent hung indefinitely waiting for a response when explicitly asked to call a tool.

**Root cause:**
The ITZ SaaS workshop instances (`api.ca-tor.watson-orchestrate.cloud.ibm.com`) do not have the Python tool execution runtime (`wxo-builder`) enabled. The tool metadata and zip artifact upload succeeds, but the execution service that actually runs the Python code returns a 404 at runtime. This is a platform/tier limitation, not a code bug.

**Confirmed by:**

- `orchestrate tools list` shows all three tools registered correctly.
- Direct API calls to `/v1/orchestrate/tools/{id}` confirm the tool spec and artifact are stored.
- The `/status` endpoint for Python tools does not exist on these instances.
- The builder service path (`/builder/v1/tools`) returns 404.
- Async Python tools use the same runtime path — setting `is_async` does not help.
- Python toolkits in draft also use the same Python tool runtime — not a workaround.

**Fix for the workshop instructions:** ✅ RESOLVED

Re-verified 2026-08-20: the runtime really is the blocker — `style: react_core` + `groq/openai/gpt-oss-120b` did **not** make Python tools execute. The OpenAPI workaround was also rejected: an OpenAPI tool's `servers.url` is called from the Orchestrate cloud, so pointing it at `http://localhost:8000` can never work, and hosting a public server (or per-attendee tunnels) is too heavy for this audience. Local MCP toolkits run inside the same Orchestrate runtime and would hit the same wall.

**Key behaviour discovered:** the dead runtime does **not** hang forever. When the agent calls a tool, it waits ~90 seconds, the tool call times out, and then the soft instruction fallback kicks in — the agent answers from its own knowledge. So the demo recovers on its own; the only cost is a ~90-second pause on the first tool call.

**Decision (for the demo):** don't hard-enforce tool use, but **keep the three tools attached to the agent** so the live "watch it decide to call a tool" moment is preserved (this is the workshop's core pitch — kept intentionally). Soften the instructions so the agent *prefers* a tool when one fits and **falls back to its own knowledge** if the tool is unavailable or errors. Net effect on these instances: the agent visibly attempts the tool, pauses ~90s, then answers from knowledge — demo never fails. On a full Orchestrate instance with the runtime enabled, the same tools execute for real and return instantly, no changes needed.

> Note: briefly tried *detaching* the tools entirely (instant answers, no hang) but reverted — it removed the tool-calling moment, which we chose to keep.

Applied to both `event_planner.yaml` (root answer key) and `index.html`:

- Removed the "you MUST always use your tools / never answer from internal knowledge" language; added an explicit knowledge-fallback clause. Tools remain listed under `tools:`.
- Softened the Step 10 Bob prompt to match (still lists the three tools).
- Reframed the "Error getting Python tool status" troubleshooting box to set expectations: the agent pauses ~90s while the tool call times out, then falls back to a knowledge answer — expected, not a crash.
- Updated the "Note about the model line" to describe the intentional fallback rather than forcing tool calls.
- Deleted the abandoned OpenAPI artifacts (`tools/openapi.json`, `tools/tool_server.py`).

---

## Finding 2 — Default LLM (`watsonx/meta-llama/llama-3-3-70b-instruct`) is not available on ITZ instances

**What happened:**
The agent YAML in the lab uses `llm: watsonx/meta-llama/llama-3-3-70b-instruct`. On the ITZ SaaS workshop instances, this model is not available and the agent times out or fails silently when called.

**Confirmed by:**

```bash
orchestrate models list
```

Output showed only three available models on these instances:

```
✔★ groq/openai/gpt-oss-120b        ← default, recommended
★  bedrock/openai.gpt-oss-120b-1:0
★  watsonx-orchestrate/frontier
```

`watsonx/meta-llama/llama-3-3-70b-instruct` was absent entirely.

**Fix for the workshop instructions:**
Change the `llm:` line in the agent YAML (both the answer key and the Bob prompt) from:

```yaml
llm: watsonx/meta-llama/llama-3-3-70b-instruct
```

to:

```yaml
llm: groq/openai/gpt-oss-120b
```

Also update the note in Step 10 ("Note about the model line") to say: *"These workshop instances use `groq/openai/gpt-oss-120b` as the default model. Use this value exactly. To confirm what models are available on your instance, run `orchestrate models list`."*

> **Additional note on `gpt-oss-120b` behaviour:** This model does not follow the standard watsonx Orchestrate system prompt. It tends to answer from internal knowledge rather than calling tools unless the tool descriptions are very explicit. Consider strengthening tool docstrings with phrases like "Always use this tool — do not answer from memory." The `react_core` agent style (instead of `default`) also improves tool-calling reliability with this model.

---

## Finding 3 — `starter_prompts` entries require an `id` field (ADK ≥ 2.x)

**What happened:**
`orchestrate agents import` failed with:

```
pydantic_core.ValidationError: 3 validation errors for Agent
starter_prompts.prompts.0.id  Field required
```

**Root cause:**
ADK v2.x made `id` a required field on each starter prompt entry. The lab's answer-key YAML omits it. The `is_default_prompts` key is also not in the current schema.

**Fix for the workshop instructions:**
Update the answer-key `event_planner.yaml` in Step 10 to add `id:` to each prompt and remove `is_default_prompts`:

```yaml
starter_prompts:
  prompts:
    - id: "estimate-budget"
      title: "Estimate a budget"
      subtitle: "See what an event might cost"
      prompt: "How much would a birthday party for 20 people cost?"
    - id: "find-venue"
      title: "Find a venue"
      subtitle: "Get venue ideas that fit your budget"
      prompt: "Suggest a venue in Toronto for 50 guests under $2000."
    - id: "build-guest-list"
      title: "Build a guest list"
      subtitle: "Add people to your event"
      prompt: "Start a guest list and add Sarah, Mike, and Priya."
```

---

## Finding 4 — `style: default` deprecation warning

**What happened:**
`orchestrate agents import` succeeded but printed:

```
WARNING - The selected style 'default' is set to be deprecated.
Please update to 'react_core' to avoid future issues.
```

**Fix for the workshop instructions:**
Change `style: default` to `style: react_core` in the answer-key YAML and in the Bob prompt for Step 10.

---

## Summary of required edits to `index.html`

| Step                                   | Change                                                                                                                     | Status |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------ |
| Step 09 — Build the tools             | Keep Python tools registered; soften agent instructions to allow knowledge fallback (see Finding 1). No OpenAPI switch.    | ✅ done |
| Step 09 — Upload tools command        | Unchanged — stays `orchestrate tools import -k python -f tools/...`                                                        | ✅ done |
| Step 10 — Agent YAML answer key       | Change`llm:` to `groq/openai/gpt-oss-120b` (Finding 2)                                                                 | ✅ done |
| Step 10 — Agent YAML answer key       | Change`style: default` to `style: react_core` (Finding 4)                                                              | ✅ done |
| Step 10 — Agent YAML answer key       | Add`id:` to each starter prompt, remove `is_default_prompts` (Finding 3)                                               | ✅ done |
| Step 10 — Bob prompt                  | Update the model name in the prompt text                                                                                   | ✅ done |
| Step 10 — "Note about the model line" | Rewrite to name`groq/openai/gpt-oss-120b` explicitly and mention `orchestrate models list`                             | ✅ done |
| Step 10 — Bob prompt                  | Change`style: default` → `style: react_core` in prompt text                                                           | ✅ done |
