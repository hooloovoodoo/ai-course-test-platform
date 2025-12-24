#!/usr/bin/env python3
"""
Batch Test Generation Script

Generates multiple test variants based on JSON configuration files in QATests directory.
Supports both English (ENG) and Serbian (SRB) languages.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from test_generator import QuestionGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load test configuration from JSON file

    Args:
        config_path: Path to JSON configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("Loaded configuration from %s", config_path)
        return config
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_path)
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in configuration file: %s", e)
        raise


def generate_test_variants(
    config: Dict[str, Any],
    language: str = None,
    num_variants: int = None,
    output_dir: str = None,
) -> list:
    """
    Generate multiple test variants based on configuration

    Args:
        config: Configuration dictionary from JSON file
        language: Override language from config ("en", "rs", or None for config default)
        num_variants: Override number of variants from config
        output_dir: Override output directory from config

    Returns:
        List of generated file paths
    """
    # Use config values or overrides
    test_name = config["name"]
    results_sheet = config["results_sheet"]
    content_config = config["content"]
    config_language = config.get("language", "both").lower()
    variants = num_variants if num_variants is not None else config.get("variants", 10)
    output = output_dir if output_dir is not None else config.get("output-dir", "/tmp")

    # Determine which languages to generate
    if language:
        languages_to_generate = [language.lower()]
    elif config_language == "both":
        languages_to_generate = ["en", "rs"]
    else:
        languages_to_generate = [config_language.lower()]

    logger.info("🎯 Generating %d variants for test '%s'", variants, test_name)

    # Create output directory if it doesn't exist
    Path(output).mkdir(parents=True, exist_ok=True)

    # Get current date for file naming
    current_date = datetime.now().strftime("%Y-%m-%d")

    generated_files = []

    # Generate for each language
    for lang in languages_to_generate:
        logger.info("📝 Generating %d variants in %s", variants, lang)

        # Initialize generator for this language
        generator = QuestionGenerator(
            name=test_name, language=lang, results_sheet=results_sheet
        )

        for variant_num in range(1, variants + 1):
            try:
                filename = f"{test_name} | {current_date} | [{lang}] | Variant {variant_num}.gs"
                output_path = os.path.join(output, filename)

                logger.info(
                    "📝 Generating variant %d/%d: %s", variant_num, variants, filename
                )

                # Generate test for the specified language
                script_content = generator.generate_test_for_language(
                    content_config=content_config,
                    language=lang,
                    output_path=output_path,
                    variant_number=variant_num,
                )

                generated_files.append(output_path)
                logger.info(
                    "✅ Generated variant %d: %d characters",
                    variant_num,
                    len(script_content),
                )

            except RuntimeError as e:
                logger.error("❌ Failed to generate variant %d: %s", variant_num, e)
                continue

    logger.info(
        "🎉 Successfully generated %d/%d test variants",
        len(generated_files),
        len(languages_to_generate) * variants,
    )
    return generated_files


def list_generated_files(
    output_dir: str = "/tmp", language: str = None, test_name: str = None
):
    """
    List all generated test files in the output directory

    Args:
        output_dir: Directory to search for test files
        language: Optional language filter ("en" or "rs")
        test_name: Optional test name filter
    """
    if test_name:
        pattern = f"{test_name} | * | *.gs"
        if language:
            pattern = f"{test_name} | * | [{language.lower()}] | *.gs"
    else:
        pattern = "* | * | *.gs"
        if language:
            pattern = f"* | * | [{language.lower()}] | *.gs"

    test_files = list(Path(output_dir).glob(pattern))

    if test_files:
        logger.info("📁 Found %d test files in %s:", len(test_files), output_dir)
        for file_path in sorted(test_files):
            file_size = file_path.stat().st_size
            logger.info("   📄 %s (%d bytes)", file_path.name, file_size)
    else:
        logger.info("📁 No test files found in %s", output_dir)

    return test_files


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate multiple test variants from JSON configuration"
    )

    parser.add_argument(
        "config",
        help="Path to JSON configuration file (e.g., QATests/l0-ai-citizen.json)",
    )

    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "rs"],
        help="Override language from config (en or rs)",
    )

    parser.add_argument(
        "--variants",
        "-n",
        type=int,
        help="Override number of test variants from config",
    )

    parser.add_argument(
        "--output-dir", "-o", help="Override output directory from config"
    )

    parser.add_argument(
        "--list-files",
        "-ls",
        action="store_true",
        help="List existing test files in output directory",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    try:
        config = load_config(args.config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("❌ Failed to load configuration: %s", e)
        return 1

    # Determine output directory for listing files
    output_dir = (
        args.output_dir if args.output_dir else config.get("output-dir", "/tmp")
    )

    # List files if requested
    if args.list_files:
        list_generated_files(output_dir, args.language, test_name=config.get("name"))
        return 0

    # Validate arguments
    variants = (
        args.variants if args.variants is not None else config.get("variants", 10)
    )
    if variants <= 0:
        logger.error("❌ Number of variants must be positive")
        return 1

    try:
        # Generate tests based on config
        all_generated_files = generate_test_variants(
            config=config,
            language=args.language,
            num_variants=args.variants,
            output_dir=args.output_dir,
        )

        # Summary
        if all_generated_files:
            logger.info(
                "🎊 Generation complete! Created %d test files",
                len(all_generated_files),
            )
            logger.info("📂 Files saved to: %s", output_dir)

            # List generated files
            list_generated_files(output_dir, test_name=config.get("name"))

            return 0

        logger.error("❌ No test files were generated")
        return 1

    except KeyboardInterrupt:
        logger.info("⏹️  Generation interrupted by user")
        return 1
    except RuntimeError as e:
        logger.error("❌ Generation failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
