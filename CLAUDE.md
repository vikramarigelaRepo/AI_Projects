# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A collection of AI agent projects. Currently contains one project: an Azure infrastructure deployment agent built with LangGraph that converts natural language into Azure deployments with human-in-the-loop approval.

## Project: azure_infra_deploy_agent

Located at `langgraph/azure_infra_deploy_agent/`.

### Setup

```bash
pip install langchain-openai langgraph pydantic python-dotenv gradio ipython
```

Create a `.env` file in the project directory:
```
AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
```

Prerequisites: Azure CLI installed and authenticated (`az login`), Bicep available (`az bicep version`).

### Running

- **Jupyter:** Open `L7_AutomateCloudDeployment.ipynb` and run cells 1–17 sequentially.
- **Gradio UI:** Run all notebook cells — the last cell launches the web interface via `demo.launch()`.

### Running Evaluations

```bash
cd langgraph/azure_infra_deploy_agent/evals
python test_parse_user_input_eval.py
```

Three evaluation patterns are implemented (see `EVAL_GUIDE.md`):
- **Outcome-Based** — direct comparison against expected outputs (fast)
- **Rubric-Based** — LLM-as-judge multi-dimensional scoring (medium)
- **Reflection** — iterative self-critique loop (slow)

## Architecture

The agent is a 7-node LangGraph workflow defined in the notebook:

```
parse_user_input → generate_infra_code → build_bicep
    → (conditional) refine_infra_code
    → prevalidate_infra_code → human_review [interrupt] → deploy_infra_with_cli → verify_deployment
```

**State:** `DeploymentAgentState` TypedDict threads through all nodes, carrying parsed parameters, generated Bicep code, build/validation/deployment results, and interrupt state.

**Human-in-the-loop:** LangGraph's `interrupt()` pauses execution at `human_review`; the Gradio UI surfaces an approve/reject button. Resumption uses a thread ID stored in `InMemorySaver` checkpoints.

**Azure execution:** Bicep operations run as subprocesses via the Azure CLI. Windows-aware path handling is used throughout.

**Supported resource types:** Storage Account, Key Vault, App Service Plan, Application Insights, Function App.
