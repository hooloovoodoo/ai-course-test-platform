#!/usr/bin/env python3
"""
Test Analyzer - Topic Redundancy Detection

This script analyzes generated test files (.gs) for topic redundancy using OpenAI's GPT-4.1.
It parses questions from the generated Google Apps Script file, identifies similar/redundant
questions, and suggests replacements based on provided course materials.

Usage:
    python test_analyzer.py --test-file "/tmp/AI Citizen | 2025-12-24 | [en] | Variant 1.gs" \
                            --materials-path /path/to/course-materials
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default prompt file path
PROMPT_FILE = "prompts/test_analyzer_prompt.md"


def load_prompt(prompt_path: str = PROMPT_FILE) -> str:
    """
    Load the LLM prompt from file

    Args:
        prompt_path: Path to the prompt file

    Returns:
        Prompt content as string
    """
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Prompt file not found: %s", prompt_path)
        raise


def parse_questions_from_gs_file(gs_file_path: str) -> List[Dict[str, Any]]:
    """
    Parse questions from a generated Google Apps Script (.gs) file

    The .gs file contains a JavaScript array like:
    const questionsPool = [
      { question: "...", choices: [...], correct: N },
      ...
    ];

    Args:
        gs_file_path: Path to the generated .gs file

    Returns:
        List of question dictionaries with 'question', 'answers', and 'correct' keys
    """
    try:
        with open(gs_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        logger.error("Test file not found: %s", gs_file_path)
        raise

    # Extract the questionsPool array from the JavaScript
    # Pattern matches: const questionsPool = [...]
    pattern = r"const questionsPool = (\[.*?\]);"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        logger.error("Could not find questionsPool in %s", gs_file_path)
        raise ValueError(f"Could not parse questions from {gs_file_path}")

    js_array = match.group(1)

    # Convert JavaScript object notation to valid JSON
    # Replace unquoted keys with quoted keys
    json_str = re.sub(r"(\s)(question|choices|correct):", r'\1"\2":', js_array)

    try:
        questions_raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse questions JSON: %s", e)
        raise ValueError(f"Could not parse questions from {gs_file_path}: {e}")

    # Convert to our standard format (correct index -> correct answer text)
    questions = []
    for q in questions_raw:
        correct_idx = q["correct"]
        choices = q["choices"]
        # Filter out "I don't know" / "Ne znam" from answers for analysis
        real_choices = [c for c in choices if c not in ("I don't know", "Ne znam")]
        correct_answer = (
            choices[correct_idx] if correct_idx < len(choices) else real_choices[0]
        )

        questions.append(
            {
                "question": q["question"],
                "answers": real_choices,
                "correct": correct_answer,
            }
        )

    logger.info("Parsed %d questions from %s", len(questions), gs_file_path)
    return questions


def load_course_materials(materials_path: str) -> str:
    """
    Load and concatenate all markdown files from the materials directory

    Args:
        materials_path: Path to directory containing markdown files

    Returns:
        Concatenated content of all markdown files
    """
    materials_dir = Path(materials_path)
    if not materials_dir.exists():
        logger.error("Materials directory not found: %s", materials_path)
        return ""

    content_parts = []
    md_files = sorted(materials_dir.glob("**/*.md"))

    for md_file in md_files:
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                file_content = f.read()
                content_parts.append(f"## {md_file.name}\n\n{file_content}")
        except Exception as e:
            logger.warning("Could not read %s: %s", md_file, e)

    logger.info("Loaded %d markdown files from %s", len(content_parts), materials_path)
    return "\n\n---\n\n".join(content_parts)


def format_questions_for_analysis(questions: List[Dict[str, Any]]) -> str:
    """
    Format questions for LLM analysis

    Args:
        questions: List of question dictionaries

    Returns:
        Formatted string representation of questions
    """
    formatted = []
    for i, q in enumerate(questions, 1):
        formatted.append(f"Q{i}: {q['question']}")
        for j, answer in enumerate(q["answers"]):
            marker = "✓" if answer == q["correct"] else " "
            formatted.append(f"  {chr(65 + j)}. [{marker}] {answer}")
        formatted.append("")

    return "\n".join(formatted)


def analyze_test_with_gpt(
    client: OpenAI,
    questions: List[Dict[str, Any]],
    course_materials: str,
    system_prompt: str,
    model: str = "gpt-4.1",
) -> str:
    """
    Analyze test questions for redundancy and suggest replacements using GPT

    Args:
        client: OpenAI client
        questions: List of test questions
        course_materials: Course materials content
        system_prompt: System prompt for the LLM
        model: Model to use for analysis

    Returns:
        Analysis result from GPT
    """
    formatted_questions = format_questions_for_analysis(questions)

    user_message = f"""## Course Materials

{course_materials}

---

## Test Questions (from generated test file)

{formatted_questions}

---

## Task

1. Analyze these questions for topic redundancy (3+ questions on the same narrow concept)
2. If redundancy is found, suggest replacement questions based on the course materials above
3. Replacement questions should cover underrepresented topics from the materials
"""

    logger.info("Sending %d questions to %s for analysis...", len(questions), model)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error("Error calling OpenAI API: %s", e)
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze generated test files for topic redundancy using GPT-4.1"
    )

    parser.add_argument(
        "--test-file",
        "-t",
        required=True,
        help="Path to generated test file (.gs) in /tmp or elsewhere",
    )

    parser.add_argument(
        "--materials-path",
        "-m",
        required=True,
        help="Path to directory containing course materials (markdown files)",
    )

    parser.add_argument(
        "--model", default="gpt-4.1", help="OpenAI model to use (default: gpt-4.1)"
    )

    parser.add_argument(
        "--prompt-file",
        "-p",
        default=PROMPT_FILE,
        help=f"Path to prompt file (default: {PROMPT_FILE})",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        print("Error: Please set the OPENAI_API_KEY environment variable")
        return 1

    try:
        # Load prompt
        logger.info("Loading prompt from %s", args.prompt_file)
        system_prompt = load_prompt(args.prompt_file)

        # Parse questions from generated test file
        logger.info("Parsing questions from %s", args.test_file)
        questions = parse_questions_from_gs_file(args.test_file)

        if not questions:
            logger.error("No questions parsed. Cannot proceed with analysis.")
            return 1

        logger.info("Parsed %d questions for analysis", len(questions))

        # Load course materials
        logger.info("Loading course materials from %s", args.materials_path)
        course_materials = load_course_materials(args.materials_path)

        if not course_materials:
            logger.warning("No course materials loaded. Analysis may be limited.")

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Perform analysis
        analysis = analyze_test_with_gpt(
            client=client,
            questions=questions,
            course_materials=course_materials,
            system_prompt=system_prompt,
            model=args.model,
        )

        # Output results
        print("\n" + "=" * 80)
        print("TEST ANALYSIS RESULTS")
        print("=" * 80)
        print(f"Test file: {args.test_file}")
        print(f"Questions analyzed: {len(questions)}")
        print("=" * 80 + "\n")
        print(analysis)
        print("\n" + "=" * 80)

        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 1
    except ValueError as e:
        logger.error("Parse error: %s", e)
        return 1
    except Exception as e:
        logger.error("Analysis failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
