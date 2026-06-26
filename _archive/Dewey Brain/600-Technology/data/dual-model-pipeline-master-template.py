# =============================================================
# DUAL-MODEL AI PIPELINE — MASTER PLATE TEMPLATE
# Blacktech Solutions Corp / Think Energy Automation
# =============================================================
# EXECUTIVE ORCHESTRATOR: Claude 4 (Anthropic Cloud API)
# CLEANING MACHINE 🧼:    phi3 / qwen2.5:1.5b (Ollama Local)
# Raspberry Pi 5 | 8GB RAM | External SSD
# Contact: leads@blacktechsolutionscorp.com
# =============================================================
#
# HOW THIS PIPELINE WORKS:
#   1. Claude (cloud) receives a task prompt and generates raw,
#      creative, human-quality text output (estimates, leads, etc.)
#   2. Ollama (local Pi) receives that raw text and converts it
#      into strict, machine-readable JSON — fast and deterministic.
#
# WHY TWO MODELS?
#   Claude is brilliant but slow and expensive for JSON cleanup.
#   Phi3/Qwen is fast, free, and perfect for structured formatting.
#   Together they form a powerful, cost-effective pipeline.
# =============================================================

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

import requests
import anthropic

# ── LOGGING SETUP ────────────────────────────────────────────
# Configures console logging so you can trace pipeline activity.
# Set level to logging.DEBUG for verbose output during development.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dual_model_pipeline")


# ── CONFIGURATION ──────────────────────────────────────────
# All tuneable settings live here. Change these to swap models,
# adjust creativity, or point at a remote Ollama instance.

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")   # Set in env
CLAUDE_MODEL      = "claude-sonnet-4-6"                  # Executive Orchestrator
OLLAMA_MODEL      = "phi3"                               # Primary Cleaner 🧼
OLLAMA_BACKUP     = "qwen2.5:1.5b"                      # Backup Cleaner
OLLAMA_BASE_URL   = "http://localhost:11434"             # Pi local Ollama server
TEMPERATURE       = 0.0                                  # Deterministic (no randomness)
MAX_TOKENS        = 1024                                 # Max output tokens from Claude

# Timeout for Ollama HTTP requests (seconds).
# Increase this if your Pi is under heavy load.
OLLAMA_TIMEOUT    = 60

# Number of parallel workers in the async batch pipeline.
PIPELINE_WORKERS  = 3


# =============================================================
# SECTION 1 — DATA MODELS
# These dataclasses define the "shape" of data moving through
# the pipeline: RawBlock flows from Claude, CleanedBlock comes
# out of Ollama ready for downstream use.
# =============================================================

@dataclass
class RawBlock:
    """
    Output from Claude — raw, possibly messy creative text.

    Produced by the ExecutiveOrchestrator.generate() method and
    handed off to the CleaningMachine for JSON formatting.

    Attributes:
        task_id   : Unique identifier (UUID4) for this task.
        content   : Raw text response from Claude.
        task_type : Category label — one of:
                    "estimate" | "lead" | "invoice" | "marketing"
        timestamp : ISO-8601 UTC timestamp of creation.
    """
    task_id:   str
    content:   str
    task_type: str   # "estimate" | "lead" | "invoice" | "marketing"
    timestamp: str


@dataclass
class CleanedBlock:
    """
    Output from Ollama — strict JSON-formatted result.

    Produced by CleaningMachine.clean() after processing a RawBlock.
    The cleaned_json field contains a fully parsed Python dict ready
    for database storage, API forwarding, or display.

    Attributes:
        task_id     : Matches the originating RawBlock.task_id.
        raw_input   : The original Claude text that was cleaned.
        cleaned_json: Parsed dict from Ollama's JSON output.
        model_used  : Which Ollama model performed the cleaning.
        success     : True if JSON was valid and parsed successfully.
        timestamp   : ISO-8601 UTC timestamp of creation.
    """
    task_id:      str
    raw_input:    str
    cleaned_json: dict
    model_used:   str
    success:      bool
    timestamp:    str


# =============================================================
# SECTION 2 — EXECUTIVE ORCHESTRATOR (Claude)
# This class wraps the Anthropic SDK and handles all Claude calls.
# It knows about task types and prepends the right system prompt
# so Claude produces rich, domain-appropriate output.
# =============================================================

# Per-task-type system prompts that prime Claude for each domain.
# These tell Claude exactly what role it's playing so the output
# is structured enough for the Cleaning Machine to parse cleanly.
TASK_SYSTEM_PROMPTS: dict[str, str] = {
    "estimate": (
        "You are a licensed master electrician and estimator for Blacktech Solutions Corp. "
        "Generate a detailed electrical estimate with line items. Include labor hours, "
        "material costs, markup percentage, and grand total. Be specific and professional."
    ),
    "lead": (
        "You are a sales qualifier for Think Energy Automation. "
        "Qualify this energy lead and extract key contact info. "
        "Score the lead's interest level (low/medium/high), identify the best product match "
        "(solar panels, battery storage, EV charger, or full system), and suggest a next action."
    ),
    "invoice": (
        "You are a billing specialist for Blacktech Solutions Corp. "
        "Generate invoice line items from this job description. "
        "Break down every billable task with quantity, unit rate, and line total. "
        "Calculate subtotal and total."
    ),
    "marketing": (
        "You are a copywriter for Think Energy battery storage solutions. "
        "Write compelling marketing copy that highlights energy independence, savings, and reliability. "
        "Target homeowners in the Chicago metro area interested in solar and battery backup systems."
    ),
}


class ExecutiveOrchestrator:
    """
    The brain of the pipeline — powered by Claude (Anthropic Cloud API).

    Responsibilities:
      - Accept a user prompt and a task type.
      - Select the correct system prompt for that task type.
      - Call the Anthropic API and return a RawBlock.

    Usage:
        orchestrator = ExecutiveOrchestrator()
        raw = orchestrator.generate("Install 200A panel upgrade", "estimate")
        print(raw.content)
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the orchestrator with an Anthropic API key.

        Args:
            api_key: Anthropic API key. Defaults to the ANTHROPIC_API_KEY
                     module-level constant (read from environment variable).

        Raises:
            ValueError: If no API key is found.
        """
        resolved_key = api_key or ANTHROPIC_API_KEY
        if not resolved_key:
            raise ValueError(
                "No Anthropic API key found. "
                "Set the ANTHROPIC_API_KEY environment variable:\n"
                "    export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.client = anthropic.Anthropic(api_key=resolved_key)
        logger.info("ExecutiveOrchestrator ready. Model: %s", CLAUDE_MODEL)

    def generate(self, prompt: str, task_type: str) -> RawBlock:
        """
        Send a prompt to Claude and return a RawBlock of raw text.

        The method prepends a domain-specific system prompt based on
        task_type so Claude produces output suited for JSON cleaning.

        Args:
            prompt:    The user-facing content/question to process.
            task_type: One of "estimate", "lead", "invoice", "marketing".
                       Controls which system prompt is injected.

        Returns:
            RawBlock: Contains Claude's raw text response, a unique
                      task_id, the task_type, and a UTC timestamp.

        Raises:
            ValueError:   If task_type is not recognized.
            RuntimeError: If the Anthropic API call fails.

        Example:
            raw = orchestrator.generate(
                "Install 20 outlets in a 3-bedroom house",
                "estimate"
            )
        """
        # Validate task type before making an expensive API call.
        if task_type not in TASK_SYSTEM_PROMPTS:
            valid = list(TASK_SYSTEM_PROMPTS.keys())
            raise ValueError(
                f"Unknown task_type '{task_type}'. Valid options: {valid}"
            )

        system_prompt = TASK_SYSTEM_PROMPTS[task_type]
        task_id = str(uuid.uuid4())

        logger.info(
            "Claude generating [task_id=%s, type=%s] prompt length=%d chars",
            task_id, task_type, len(prompt),
        )

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract the text from the first content block.
            raw_content = response.content[0].text

        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Anthropic authentication failed. "
                "Check your ANTHROPIC_API_KEY is valid and not expired."
            )
        except anthropic.RateLimitError:
            raise RuntimeError(
                "Anthropic rate limit hit. "
                "Wait a moment and retry, or upgrade your plan."
            )
        except anthropic.APIConnectionError as exc:
            raise RuntimeError(
                f"Could not connect to Anthropic API. "
                f"Check your internet connection. Detail: {exc}"
            )
        except anthropic.APIError as exc:
            raise RuntimeError(f"Anthropic API error: {exc}")

        logger.info(
            "Claude response received [task_id=%s] length=%d chars",
            task_id, len(raw_content),
        )

        return RawBlock(
            task_id=task_id,
            content=raw_content,
            task_type=task_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# =============================================================
# SECTION 3 — CLEANING MACHINE 🧼 (Ollama / Local)
# This class calls the local Ollama server on the Raspberry Pi.
# Its only job: take messy Claude text → return strict JSON.
# It never adds creative content — pure formatting only.
# =============================================================

# System prompt injected into every Ollama cleaning request.
# Extremely directive: JSON only, no explanations, no markdown.
OLLAMA_SYSTEM_PROMPT = (
    "You are a JSON formatter. Convert the input to strict valid JSON only. "
    "No explanation. No markdown. No code fences. Raw JSON only. "
    "Output must be parseable by Python's json.loads() with zero modifications."
)


class CleaningMachine:
    """
    The formatter of the pipeline — powered by Ollama (local Pi).

    Responsibilities:
      - Accept a RawBlock from Claude.
      - POST it to the local Ollama /api/generate endpoint.
      - Parse the JSON response and return a CleanedBlock.
      - Automatically fall back from phi3 → qwen2.5:1.5b if needed.

    Why local?
      Running the cleaner on-device (Raspberry Pi 5) keeps JSON
      formatting costs at $0 and latency under 5 seconds.

    Usage:
        cleaner = CleaningMachine()
        cleaned = cleaner.clean(raw_block)
        print(cleaned.cleaned_json)
    """

    def __init__(
        self,
        primary_model: str = OLLAMA_MODEL,
        backup_model: str = OLLAMA_BACKUP,
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        """
        Initialize the cleaning machine.

        Args:
            primary_model: Ollama model to try first (default: phi3).
            backup_model:  Fallback model if primary fails (default: qwen2.5:1.5b).
            base_url:      Ollama server URL (default: http://localhost:11434).
        """
        self.primary_model = primary_model
        self.backup_model  = backup_model
        self.base_url      = base_url.rstrip("/")
        self.generate_url  = f"{self.base_url}/api/generate"
        logger.info(
            "CleaningMachine ready. Primary: %s | Backup: %s | URL: %s",
            self.primary_model, self.backup_model, self.base_url,
        )

    def _call_ollama(self, model: str, user_content: str) -> str:
        """
        Make a single POST request to the Ollama /api/generate endpoint.

        Args:
            model:        Ollama model name (e.g. "phi3").
            user_content: The text to format into JSON.

        Returns:
            The raw text response from Ollama.

        Raises:
            requests.RequestException: On network or HTTP error.
            RuntimeError:              If Ollama returns a non-200 status.
        """
        payload = {
            "model":  model,
            "prompt": user_content,
            "system": OLLAMA_SYSTEM_PROMPT,
            "stream": False,          # Single complete response (not streamed)
            "options": {
                "temperature": TEMPERATURE,   # 0.0 = fully deterministic
                "num_predict": MAX_TOKENS,
            },
        }

        logger.debug("Ollama POST [model=%s] payload length=%d", model, len(user_content))

        response = requests.post(
            self.generate_url,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        return data.get("response", "")

    def _extract_json(self, text: str) -> dict:
        """
        Extract and parse a JSON dict from Ollama's text output.

        Handles common edge cases:
          - Leading/trailing whitespace
          - Accidental markdown code fences (```json ... ```)
          - JSON embedded inside a longer string

        Args:
            text: Raw text response from Ollama.

        Returns:
            Parsed Python dict.

        Raises:
            ValueError: If no valid JSON object can be found.
        """
        # Strip whitespace and remove markdown code fences if present.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove ```json\n...\n``` or ```\n...\n```
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

        # Attempt direct parse first (fastest path).
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt to find the first complete JSON object in the string.
        # Scans for { ... } boundaries to extract embedded JSON.
        start = cleaned.find("{")
        end   = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not extract valid JSON from Ollama output. "
            f"Raw output (first 300 chars): {text[:300]}"
        )

    def clean(self, raw: RawBlock) -> CleanedBlock:
        """
        Convert a RawBlock's content into strict JSON using Ollama.

        Attempts the primary model (phi3) first. If it fails for any
        reason (model not found, JSON parse error, timeout), it
        automatically retries with the backup model (qwen2.5:1.5b).
        If both fail, returns a CleanedBlock with success=False and
        an error dict in cleaned_json for easy debugging.

        Args:
            raw: A RawBlock produced by ExecutiveOrchestrator.generate().

        Returns:
            CleanedBlock: Always returns — never raises. Check .success
                          to determine if cleaning succeeded.

        Example:
            cleaned = cleaner.clean(raw_block)
            if cleaned.success:
                process(cleaned.cleaned_json)
            else:
                logger.error("Cleaning failed: %s", cleaned.cleaned_json)
        """
        # Build the cleaning prompt — include task context for better JSON shaping.
        cleaning_prompt = (
            f"Task type: {raw.task_type}\n"
            f"Convert the following text to strict JSON:\n\n"
            f"{raw.content}"
        )

        # Try primary model, then fall back to backup.
        for model in (self.primary_model, self.backup_model):
            logger.info(
                "CleaningMachine attempting [task_id=%s, model=%s]",
                raw.task_id, model,
            )
            try:
                raw_response = self._call_ollama(model, cleaning_prompt)
                parsed_json  = self._extract_json(raw_response)

                logger.info(
                    "Cleaning SUCCESS [task_id=%s, model=%s] keys=%s",
                    raw.task_id, model, list(parsed_json.keys()),
                )

                return CleanedBlock(
                    task_id=raw.task_id,
                    raw_input=raw.content,
                    cleaned_json=parsed_json,
                    model_used=model,
                    success=True,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            except requests.ConnectionError:
                logger.warning(
                    "Could not connect to Ollama at %s. "
                    "Is Ollama running? (ollama serve)",
                    self.base_url,
                )
            except requests.Timeout:
                logger.warning(
                    "Ollama timed out after %ds [model=%s]. "
                    "Pi may be under load. Try increasing OLLAMA_TIMEOUT.",
                    OLLAMA_TIMEOUT, model,
                )
            except (RuntimeError, ValueError) as exc:
                logger.warning(
                    "Cleaning failed [model=%s]: %s", model, exc
                )

        # Both models failed — return a failure CleanedBlock so the
        # pipeline can continue and callers can handle gracefully.
        logger.error(
            "ALL cleaners FAILED [task_id=%s]. Returning error block.",
            raw.task_id,
        )
        return CleanedBlock(
            task_id=raw.task_id,
            raw_input=raw.content,
            cleaned_json={"error": "cleaning_failed", "raw_text": raw.content[:500]},
            model_used="none",
            success=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# =============================================================
# SECTION 4 — ASYNC BATCH PIPELINE
# For processing many prompts at once (bulk lead imports, batch
# estimates, etc.). Uses asyncio + a thread pool so blocking
# HTTP calls (Claude + Ollama) don't stall each other.
#
# Architecture:
#   feeder  → asyncio.Queue → [worker1, worker2, worker3] → results
#
# The feeder generates all RawBlocks first (Claude calls are
# sequential to avoid rate limits), then workers clean in parallel
# using thread executor pools for the blocking requests.
# =============================================================

class DualModelPipeline:
    """
    Asynchronous batch pipeline combining Claude + Ollama.

    Processes a list of prompts efficiently:
      - Claude calls are made sequentially (API rate limit friendly).
      - Ollama cleaning runs in parallel across PIPELINE_WORKERS threads.
      - Results are collected and returned in original input order.

    Usage:
        pipeline = DualModelPipeline()
        prompts = [
            {"prompt": "Install 200A panel", "task_type": "estimate"},
            {"prompt": "Jane Doe, 312-555-0001, wants battery backup", "task_type": "lead"},
        ]
        results = asyncio.run(pipeline.run_batch(prompts))
        for block in results:
            print(block.cleaned_json)
    """

    def __init__(self) -> None:
        """
        Initialize the pipeline with an orchestrator and cleaner.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set.
        """
        self.orchestrator = ExecutiveOrchestrator()
        self.cleaner      = CleaningMachine()

    async def _feeder(
        self,
        prompts: list[dict],
        queue: asyncio.Queue,
    ) -> None:
        """
        Generate RawBlocks from Claude and place them into the queue.

        Runs sequentially to stay within Anthropic rate limits.
        Each RawBlock is placed in the queue as soon as it's ready
        so workers can begin cleaning immediately.

        Args:
            prompts: List of dicts with keys "prompt" and "task_type".
            queue:   asyncio.Queue shared with worker coroutines.
        """
        loop = asyncio.get_event_loop()

        for i, item in enumerate(prompts):
            prompt    = item.get("prompt", "")
            task_type = item.get("task_type", "estimate")

            print(f"  [Feeder] Generating {i + 1}/{len(prompts)}: {task_type}")

            try:
                # Run the blocking Claude call in a thread so the event
                # loop stays responsive while waiting for the API.
                raw = await loop.run_in_executor(
                    None,
                    lambda p=prompt, t=task_type: self.orchestrator.generate(p, t),
                )
                await queue.put((i, raw))  # (original_index, raw_block)
            except Exception as exc:
                logger.error("Feeder error on item %d: %s", i, exc)
                # Push a sentinel error block so the index slot is filled.
                error_raw = RawBlock(
                    task_id=str(uuid.uuid4()),
                    content=f"ERROR: {exc}",
                    task_type=task_type,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                await queue.put((i, error_raw))

        # Signal workers that feeding is complete by pushing sentinel values.
        for _ in range(PIPELINE_WORKERS):
            await queue.put(None)

    async def _worker(
        self,
        worker_id: int,
        queue: asyncio.Queue,
        results: dict,
        total: int,
    ) -> None:
        """
        Pull RawBlocks from the queue and clean them with Ollama.

        Args:
            worker_id: Integer ID for logging.
            queue:     Shared asyncio.Queue with the feeder.
            results:   Shared dict mapping original_index → CleanedBlock.
            total:     Total number of prompts (for progress display).
        """
        loop = asyncio.get_event_loop()

        while True:
            item = await queue.get()

            # None is the sentinel value — no more work.
            if item is None:
                queue.task_done()
                break

            original_index, raw = item
            completed = len(results) + 1
            print(f"  [Worker-{worker_id}] Processing {completed}/{total}: {raw.task_type}")

            try:
                # Run the blocking Ollama call in a thread executor.
                cleaned = await loop.run_in_executor(
                    None,
                    lambda r=raw: self.cleaner.clean(r),
                )
            except Exception as exc:
                logger.error("Worker %d error: %s", worker_id, exc)
                cleaned = CleanedBlock(
                    task_id=raw.task_id,
                    raw_input=raw.content,
                    cleaned_json={"error": str(exc)},
                    model_used="none",
                    success=False,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            results[original_index] = cleaned
            queue.task_done()

    async def run_batch(self, prompts: list[dict]) -> list[CleanedBlock]:
        """
        Process a batch of prompts through the full dual-model pipeline.

        Coordinates the feeder and worker pool, then assembles and
        returns results in the same order as the input list.

        Args:
            prompts: List of dicts. Each dict must have:
                       - "prompt"    : str  — the user content/question
                       - "task_type" : str  — "estimate"|"lead"|"invoice"|"marketing"

        Returns:
            List of CleanedBlock in the same order as input prompts.
            Always returns one CleanedBlock per input item.

        Example:
            pipeline = DualModelPipeline()
            results = asyncio.run(pipeline.run_batch([
                {"prompt": "200A panel upgrade", "task_type": "estimate"},
                {"prompt": "Maria Lopez, wants solar", "task_type": "lead"},
            ]))
        """
        if not prompts:
            return []

        total = len(prompts)
        print(f"\n🚀 Starting batch pipeline: {total} item(s), {PIPELINE_WORKERS} workers")

        # Shared structures for feeder ↔ worker coordination.
        queue:   asyncio.Queue      = asyncio.Queue(maxsize=total * 2)
        results: dict[int, CleanedBlock] = {}

        # Launch the feeder and all workers as concurrent coroutines.
        feeder_task  = asyncio.create_task(self._feeder(prompts, queue))
        worker_tasks = [
            asyncio.create_task(
                self._worker(worker_id=i + 1, queue=queue, results=results, total=total)
            )
            for i in range(PIPELINE_WORKERS)
        ]

        # Wait for feeder to finish pushing all items.
        await feeder_task
        # Wait for all workers to drain the queue.
        await asyncio.gather(*worker_tasks)

        print(f"✅ Batch complete: {len(results)}/{total} cleaned\n")

        # Reassemble results in original input order.
        return [results[i] for i in range(total)]


# =============================================================
# SECTION 5 — USE CASE FUNCTIONS
# Four high-level convenience functions for common Blacktech /
# Think Energy workflows. These are the "public API" — call these
# directly without touching the class internals.
# =============================================================

def generate_estimate(job_description: str) -> dict:
    """
    Generate a Blacktech electrical estimate from a job description.

    Sends the job description to Claude to generate a detailed
    estimate narrative, then cleans it into a structured JSON object
    with line items, labor, markup, and grand total.

    Args:
        job_description: Plain-English description of the electrical job.
                         e.g. "Install 20 outlets and 10 switches in a
                              3-bedroom house, Chicago IL"

    Returns:
        dict with keys:
          - customer    : str  — customer name (if extractable)
          - address     : str  — job site address
          - labor_hours : float — total estimated labor hours
          - labor_rate  : float — hourly labor rate ($)
          - labor_total : float — labor_hours × labor_rate
          - markup_pct  : float — material markup percentage
          - grand_total : float — total job cost
          - line_items  : list[dict] — each with description, qty, unit, cost

    Example:
        est = generate_estimate("Install 200A main panel in 2-flat building")
        print(f"Grand total: ${est['grand_total']:.2f}")
    """
    orchestrator = ExecutiveOrchestrator()
    cleaner      = CleaningMachine()

    # Build a structured prompt that guides Claude to include all
    # the fields we need in the output (makes cleaning easier).
    prompt = (
        f"Job description: {job_description}\n\n"
        "Create a detailed electrical estimate. Include:\n"
        "- Customer name and address (use 'TBD' if not provided)\n"
        "- Estimated labor hours and hourly rate\n"
        "- Material costs with line items (description, qty, unit cost)\n"
        "- Material markup percentage\n"
        "- Labor total, materials total, and grand total\n"
        "Format your response so it can be converted to JSON with these keys: "
        "customer, address, labor_hours, labor_rate, labor_total, markup_pct, "
        "grand_total, line_items (array of {description, qty, unit, cost})"
    )

    raw     = orchestrator.generate(prompt, "estimate")
    cleaned = cleaner.clean(raw)
    return cleaned.cleaned_json


def qualify_lead(lead_info: str) -> dict:
    """
    Qualify a Think Energy energy lead and extract structured contact info.

    Sends raw lead information (from a web form, SMS, or cold call notes)
    to Claude for analysis and scoring, then cleans into a JSON lead card.

    Args:
        lead_info: Raw lead details as freeform text.
                   e.g. "John Smith, 773-555-1234, interested in solar + battery,
                        homeowner in Oak Park, mentioned high ComEd bills"

    Returns:
        dict with keys:
          - name                : str  — full name
          - phone               : str  — phone number
          - email               : str  — email (or "not provided")
          - address             : str  — home/property address
          - interest_level      : str  — "low" | "medium" | "high"
          - recommended_product : str  — best Think Energy product match
          - next_action         : str  — suggested follow-up step

    Example:
        lead = qualify_lead("Maria Lopez, 312-555-0001, wants whole-home backup battery")
        print(f"Interest: {lead['interest_level']} → {lead['next_action']}")
    """
    orchestrator = ExecutiveOrchestrator()
    cleaner      = CleaningMachine()

    prompt = (
        f"Lead information: {lead_info}\n\n"
        "Qualify this energy lead. Provide:\n"
        "- Full name, phone number, email address\n"
        "- Property address or service area\n"
        "- Interest level (low/medium/high) with reasoning\n"
        "- Best recommended product (solar panels, battery storage, "
        "  EV charger, solar+battery bundle, or full energy system)\n"
        "- Clear next action step for the sales rep\n"
        "Format as JSON with keys: name, phone, email, address, "
        "interest_level, recommended_product, next_action"
    )

    raw     = orchestrator.generate(prompt, "lead")
    cleaned = cleaner.clean(raw)
    return cleaned.cleaned_json


def format_invoice(job_data: str) -> dict:
    """
    Format raw job notes into structured invoice line items.

    Takes rough field notes or job completion summaries and converts
    them into a clean, billable invoice structure ready for QBO import.

    Args:
        job_data: Raw job notes, completion summary, or work order text.
                  e.g. "Replaced 2 circuit breakers, ran new 20A circuit
                        to kitchen, 4 hours labor, $180 in parts"

    Returns:
        dict with keys:
          - invoice_items : list[dict] — each with:
              - description : str   — line item description
              - qty         : float — quantity
              - rate        : float — unit rate ($)
              - amount      : float — qty × rate
          - subtotal       : float — sum of all line amounts
          - total          : float — subtotal (add tax separately)

    Example:
        inv = format_invoice("Installed EV charger, 8hrs labor, $420 parts")
        print(f"Invoice total: ${inv['total']:.2f}")
    """
    orchestrator = ExecutiveOrchestrator()
    cleaner      = CleaningMachine()

    prompt = (
        f"Job data: {job_data}\n\n"
        "Extract all billable line items for an invoice. For each item provide:\n"
        "- Description of work or material\n"
        "- Quantity (hours for labor, units for materials)\n"
        "- Unit rate (dollars)\n"
        "- Line total (qty × rate)\n"
        "Then calculate subtotal and total.\n"
        "Format as JSON with keys: invoice_items (array of {description, qty, rate, amount}), "
        "subtotal, total"
    )

    raw     = orchestrator.generate(prompt, "invoice")
    cleaned = cleaner.clean(raw)
    return cleaned.cleaned_json


def generate_marketing_copy(topic: str) -> dict:
    """
    Generate Think Energy / battery storage marketing content.

    Uses Claude's creative capabilities to write compelling copy for
    a given topic, then structures it into reusable JSON fields for
    website, SMS, email, or social media use.

    Args:
        topic: Marketing topic or campaign focus.
               e.g. "summer energy savings with home battery storage"
               e.g. "why Chicago homeowners need solar + battery backup"

    Returns:
        dict with keys:
          - headline        : str — main attention-grabbing headline
          - body            : str — 2-3 paragraph marketing copy
          - call_to_action  : str — CTA text (e.g. "Get a free quote today!")
          - target_audience : str — description of intended reader

    Example:
        copy = generate_marketing_copy("EV charger + solar bundle promotion")
        print(copy['headline'])
        print(copy['call_to_action'])
    """
    orchestrator = ExecutiveOrchestrator()
    cleaner      = CleaningMachine()

    prompt = (
        f"Marketing topic: {topic}\n\n"
        "Write persuasive marketing copy for Think Energy Automation, "
        "a Chicago-area company offering solar panels, battery storage (Powerwall / Enphase), "
        "and EV chargers to homeowners. The copy should:\n"
        "- Lead with a powerful, curiosity-driving headline\n"
        "- Explain the core benefit in 2-3 short paragraphs\n"
        "- End with a clear, urgent call to action\n"
        "- Target Chicago-area homeowners aged 35-65, energy-conscious\n"
        "Format as JSON with keys: headline, body, call_to_action, target_audience"
    )

    raw     = orchestrator.generate(prompt, "marketing")
    cleaned = cleaner.clean(raw)
    return cleaned.cleaned_json


# =============================================================
# SECTION 6 — MAIN DEMO BLOCK
# Run this file directly to test the pipeline end-to-end.
# Make sure Ollama is running and ANTHROPIC_API_KEY is set.
#
#   export ANTHROPIC_API_KEY=sk-ant-...
#   ollama serve &
#   python dual-model-pipeline-master-template.py
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  DUAL-MODEL PIPELINE TEST")
    print("  Blacktech Solutions Corp / Think Energy Automation")
    print("=" * 60)

    # ── TEST 1: Electrical Estimate ────────────────────────────
    print("\n[TEST 1] Generating electrical estimate...")
    try:
        result = generate_estimate(
            "Install 20 outlets and 10 switches in a 3-bedroom house in Chicago, IL"
        )
        print("ESTIMATE:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"  ⚠️  Estimate test failed: {e}")

    # ── TEST 2: Lead Qualification ─────────────────────────────
    print("\n[TEST 2] Qualifying energy lead...")
    try:
        result = qualify_lead(
            "John Smith, 773-555-1234, interested in solar + battery, "
            "homeowner in Evanston IL, said his ComEd bill is $350/month"
        )
        print("LEAD:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"  ⚠️  Lead test failed: {e}")

    # ── TEST 3: Invoice Formatting ─────────────────────────────
    print("\n[TEST 3] Formatting invoice...")
    try:
        result = format_invoice(
            "Replaced main panel 100A to 200A upgrade, ran 3 new circuits, "
            "installed 2 GFCI outlets, 12 hours labor, $850 in materials"
        )
        print("INVOICE:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"  ⚠️  Invoice test failed: {e}")

    # ── TEST 4: Marketing Copy ─────────────────────────────────
    print("\n[TEST 4] Generating marketing copy...")
    try:
        result = generate_marketing_copy(
            "home battery backup systems for Chicago homeowners worried about power outages"
        )
        print("MARKETING COPY:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"  ⚠️  Marketing test failed: {e}")

    # ── TEST 5: Async Batch Pipeline ───────────────────────────
    print("\n[TEST 5] Running async batch pipeline (2 items)...")
    try:
        pipeline = DualModelPipeline()
        batch_prompts = [
            {
                "prompt": "Install EV charger in 2-car garage, Oak Park IL",
                "task_type": "estimate",
            },
            {
                "prompt": (
                    "Maria Gonzalez, 708-555-9988, saw our yard sign, "
                    "wants to go fully off-grid, house in Berwyn IL"
                ),
                "task_type": "lead",
            },
        ]
        batch_results = asyncio.run(pipeline.run_batch(batch_prompts))

        for i, block in enumerate(batch_results):
            status = "✅" if block.success else "❌"
            print(f"\nBatch item {i + 1} {status} [model: {block.model_used}]:")
            print(json.dumps(block.cleaned_json, indent=2))
    except Exception as e:
        print(f"  ⚠️  Batch pipeline test failed: {e}")

    print("\n" + "=" * 60)
    print("  PIPELINE TEST COMPLETE")
    print("=" * 60)


# =============================================================
# REQUIREMENTS:
# pip install anthropic requests
# ollama pull phi3
# ollama pull qwen2.5:1.5b
# export ANTHROPIC_API_KEY=your_key_here
#
# HARDWARE: Raspberry Pi 5, 8GB RAM, External SSD
# MODELS:   phi3 (2.2GB) primary cleaner
#           qwen2.5:1.5b (1GB) backup cleaner
#           claude-sonnet-4-6 (cloud) executive orchestrator
# PORT:     Ollama runs on localhost:11434
#
# QUICK START:
#   1. Install deps:  pip install anthropic requests
#   2. Pull models:   ollama pull phi3 && ollama pull qwen2.5:1.5b
#   3. Start Ollama:  ollama serve
#   4. Set API key:   export ANTHROPIC_API_KEY=sk-ant-...
#   5. Run test:      python dual-model-pipeline-master-template.py
#
# TROUBLESHOOTING:
#   - "No API key" error   → Check: echo $ANTHROPIC_API_KEY
#   - "Connection refused" → Ollama not running: ollama serve
#   - "Model not found"    → ollama pull phi3
#   - Slow cleaning        → Normal on Pi 5; phi3 ~3-8s per call
#   - JSON parse errors    → Backup model (qwen2.5:1.5b) triggers auto
# =============================================================
