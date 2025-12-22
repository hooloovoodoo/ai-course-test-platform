#!/usr/bin/env python3
"""
Batch Quiz Generation Script

Generates multiple quiz variants for specified language(s) and saves them to /tmp directory.
Supports both English (ENG) and Serbian (SRB) languages with the new file structure.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from quiz_generator import QuestionGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_quiz_variants(
    language: str = "ENG",
    num_variants: int = 10,
    output_dir: str = "/tmp",
    results_sheet: str = "1ACSRHmuU_Jg1NuPsErYye3kXg64C2ibfk8omg3vKlsA"
    ) -> list:
    """
    Generate multiple quiz variants for the specified language

    Args:
        language: Language code ("ENG" or "SRB")
        num_variants: Number of quiz variants to generate
        output_dir: Directory to save generated quiz files
        results_sheet: Google Sheets document ID to store results

    Returns:
        List of generated file paths
    """

    logger.info("🎯 Generating %d quiz variants in %s", num_variants, language)

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get current date for file naming
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Initialize generator
    generator = QuestionGenerator(language=language, results_sheet=results_sheet)

    generated_files = []

    for variant_num in range(1, num_variants + 1):
        try:
            filename = f"AI Coder | {current_date} | [{language}] | Variant {variant_num}.gs"
            output_path = os.path.join(output_dir, filename)

            logger.info("📝 Generating variant %d/%d: %s",
                        variant_num, num_variants, filename)

            # Generate quiz for the specified language
            script_content = generator.generate_quiz_for_language(
                language=language,
                output_path=output_path,
                variant_number=variant_num
            )

            generated_files.append(output_path)
            logger.info("✅ Generated variant %d: %d characters", variant_num, len(script_content))

        except RuntimeError as e:
            logger.error("❌ Failed to generate variant %d: %s", variant_num, e)
            continue

    logger.info("🎉 Successfully generated %d/%d quiz variants",
                len(generated_files), num_variants)
    return generated_files


def list_generated_files(output_dir: str = "/tmp", language: str = None):
    """
    List all generated quiz files in the output directory

    Args:
        output_dir: Directory to search for quiz files
        language: Optional language filter ("ENG" or "SRB")
    """

    pattern = "AI Coder | * | *.gs"
    if language:
        pattern = f"AI Coder | * | [{language.upper()}] | *.gs"

    quiz_files = list(Path(output_dir).glob(pattern))

    if quiz_files:
        logger.info("📁 Found %d quiz files in %s:", len(quiz_files), output_dir)
        for file_path in sorted(quiz_files):
            file_size = file_path.stat().st_size
            logger.info("   📄 %s (%d bytes)", file_path.name, file_size)
    else:
        logger.info("📁 No quiz files found in %s", output_dir)

    return quiz_files


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate multiple quizes')

    parser.add_argument(
        '--language', '-l',
        choices=['ENG', 'SRB', 'BOTH'],
        default='ENG',
        help='Language for quiz generation (default: ENG)'
    )

    parser.add_argument(
        '--variants', '-n',
        type=int,
        default=10,
        help='Number of quiz variants to generate (default: 10)'
    )

    parser.add_argument(
        '--output-dir', '-o',
        default='/tmp',
        help='Output directory for generated files (default: /tmp)'
    )

    parser.add_argument(
        '--list-files', '-ls',
        action='store_true',
        help='List existing quiz files in output directory'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--results-sheet',
        '-r',
        default='1ACSRHmuU_Jg1NuPsErYye3kXg64C2ibfk8omg3vKlsA',
        help='Google Sheets document ID to store results'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # List files if requested
    if args.list_files:
        list_generated_files(
            args.output_dir, args.language if args.language != 'BOTH' else None)
        return 0

    # Validate arguments
    if args.variants <= 0:
        logger.error("❌ Number of variants must be positive")
        return 1

    try:
        all_generated_files = []

        if args.language == 'BOTH':
            # Generate for both languages
            logger.info("🌐 Generating quizzes for both languages")

            # Generate English variants
            eng_files = generate_quiz_variants(
                'ENG', args.variants, args.output_dir)
            all_generated_files.extend(eng_files)

            # Generate Serbian variants
            srb_files = generate_quiz_variants(
                'SRB', args.variants, args.output_dir)
            all_generated_files.extend(srb_files)

        else:
            # Generate for single language
            generated_files = generate_quiz_variants(
                args.language, args.variants, args.output_dir)
            all_generated_files.extend(generated_files)

        # Summary
        if all_generated_files:
            logger.info("🎊 Generation complete! Created %d quiz files",
                        len(all_generated_files))
            logger.info("📂 Files saved to: %s", args.output_dir)

            # List generated files
            list_generated_files(args.output_dir)

            return 0

        logger.error("❌ No quiz files were generated")
        return 1

    except KeyboardInterrupt:
        logger.info("⏹️  Generation interrupted by user")
        return 1
    except RuntimeError as e:
        logger.error("❌ Generation failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
