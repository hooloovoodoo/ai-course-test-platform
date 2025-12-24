#!/usr/bin/env python3
"""
Test Analyzer - Topic Redundancy Detection

This script analyzes test questions for topic redundancy using OpenAI's GPT-4.1.
It loads course materials and test configurations, then identifies questions
that may be too similar or cover the same narrow topic excessively.

Usage:
    python test_analyzer.py --test-config QATests/l0-ai-citizen.json \
                            --materials-path /path/to/course-materials \
                            --language en
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Prompt file not found: %s", prompt_path)
        raise


def load_test_config(config_path: str) -> Dict[str, Any]:
    """
    Load test configuration from JSON file

    Args:
        config_path: Path to test configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Test configuration file not found: %s", config_path)
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in configuration file: %s", e)
        raise


def load_questions_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load questions from a JSON file

    Args:
        file_path: Path to questions JSON file

    Returns:
        List of question dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Questions file not found: %s", file_path)
        return []
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in questions file %s: %s", file_path, e)
        return []


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
            with open(md_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                content_parts.append(f"## {md_file.name}\n\n{file_content}")
        except Exception as e:
            logger.warning("Could not read %s: %s", md_file, e)

    logger.info("Loaded %d markdown files from %s", len(content_parts), materials_path)
    return "\n\n---\n\n".join(content_parts)


def get_test_questions(
    config: Dict[str, Any],
    language: str,
    base_path: str = "."
) -> List[Dict[str, Any]]:
    """
    Load all questions for a test based on configuration

    Args:
        config: Test configuration dictionary
        language: Language code ("en" or "rs")
        base_path: Base path for question files

    Returns:
        List of all questions for the test
    """
    content_config = config.get('content', {})
    all_questions = []

    for relative_path, count in content_config.items():
        full_path = Path(base_path) / "QAPool" / language / relative_path.lstrip('/')
        questions = load_questions_from_file(str(full_path))

        # Take the specified number of questions (in order, no shuffling)
        selected = questions[:count]
        all_questions.extend(selected)

        logger.info("Loaded %d/%d questions from %s",
                    len(selected), count, relative_path)

    return all_questions


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
        for j, answer in enumerate(q['answers']):
            marker = "✓" if answer == q['correct'] else " "
            formatted.append(f"  {chr(65+j)}. [{marker}] {answer}")
        formatted.append("")

    return "\n".join(formatted)


def analyze_test_with_gpt(
    client: OpenAI,
    questions: List[Dict[str, Any]],
    course_materials: str,
    system_prompt: str,
    model: str = "gpt-4.1"
) -> str:
    """
    Analyze test questions for redundancy using GPT

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

## Test Questions

{formatted_questions}
"""

    logger.info("Sending %d questions to %s for analysis...", len(questions), model)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=4000
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error("Error calling OpenAI API: %s", e)
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze test questions for topic redundancy using GPT-4.1'
    )

    parser.add_argument(
        '--test-config', '-c',
        required=True,
        help='Path to test configuration file (e.g., QATests/l0-ai-citizen.json)'
    )

    parser.add_argument(
        '--materials-path', '-m',
        required=True,
        help='Path to directory containing course materials (markdown files)'
    )

    parser.add_argument(
        '--language', '-l',
        choices=['en', 'rs'],
        default='en',
        help='Language of questions to analyze (default: en)'
    )

    parser.add_argument(
        '--model',
        default='gpt-4.1',
        help='OpenAI model to use (default: gpt-4.1)'
    )

    parser.add_argument(
        '--base-path', '-b',
        default='.',
        help='Base path for question files (default: current directory)'
    )

    parser.add_argument(
        '--prompt-file', '-p',
        default=PROMPT_FILE,
        help=f'Path to prompt file (default: {PROMPT_FILE})'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        print("Error: Please set the OPENAI_API_KEY environment variable")
        return 1

    try:
        # Load prompt
        logger.info("Loading prompt from %s", args.prompt_file)
        system_prompt = load_prompt(args.prompt_file)

        # Load test configuration
        logger.info("Loading test configuration from %s", args.test_config)
        config = load_test_config(args.test_config)

        # Load course materials
        logger.info("Loading course materials from %s", args.materials_path)
        course_materials = load_course_materials(args.materials_path)

        if not course_materials:
            logger.warning("No course materials loaded. Analysis may be limited.")

        # Load questions
        logger.info("Loading test questions for language: %s", args.language)
        questions = get_test_questions(config, args.language, args.base_path)

        if not questions:
            logger.error("No questions loaded. Cannot proceed with analysis.")
            return 1

        logger.info("Loaded %d questions for analysis", len(questions))

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Perform analysis
        analysis = analyze_test_with_gpt(
            client=client,
            questions=questions,
            course_materials=course_materials,
            system_prompt=system_prompt,
            model=args.model
        )

        # Output results
        print("\n" + "=" * 80)
        print("TEST ANALYSIS RESULTS")
        print("=" * 80 + "\n")
        print(analysis)
        print("\n" + "=" * 80)

        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 1
    except Exception as e:
        logger.error("Analysis failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
