#!/usr/bin/env python3
"""
AI Quiz System - Main Entry Point

This script provides a unified interface for the complete AI quiz:
1. Generate quiz variants in multiple languages (quiz_generator_batch.py)
2. Deploy quizzes to Google Apps Script (gas_deployer_batch.py)
3. Send bilingual email notifications (email_notifier.py)

Usage Examples:
    # Generate 10 English quiz variants
    python main.py generate --language ENG --variants 10

    # Generate 5 variants for both languages
    python main.py generate --language BOTH --variants 5

    # Deploy all English quizzes
    python main.py deploy --language ENG

    # Send emails with quiz URLs
    python main.py email en_urls.txt sr_urls.txt recipients.txt
"""

import argparse
import logging
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIQuizOrchestrator:
    """Main orchestrator for the AI quiz system"""

    def __init__(self):
        """Initialize the orchestrator"""
        self.base_dir = Path(__file__).parent
        self.venv_python = self.base_dir / "venv" / "bin" / "python"

        # Check if virtual environment exists
        if not self.venv_python.exists():
            logger.warning("Virtual environment not found. Using system Python.")
            self.python_cmd = "python"
        else:
            self.python_cmd = str(self.venv_python)

    def run_script(self, script_name: str, args: List[str]) -> bool:
        """
        Run a script with the given arguments

        Args:
            script_name: Name of the script to run
            args: List of command line arguments

        Returns:
            True if script ran successfully, False otherwise
        """
        script_path = self.base_dir / script_name
        if not script_path.exists():
            logger.error("Script not found: %s", script_path)
            return False

        cmd = [self.python_cmd, str(script_path)] + args
        logger.info("Running: %s",' '.join(cmd))

        try:
            result = subprocess.run(cmd, check=True, cwd=self.base_dir)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            logger.error("Script failed with exit code %d", e.returncode)
            return False
        except RuntimeError as e:
            logger.error("RuntimeError running script: %s", e)
            return False

    def generate_quizzes(
        self,
        language: str = "ENG",
        variants: int = 10,
        output_dir: str = "/tmp",
        results_sheet: str = "1ACSRHmuU_Jg1NuPsErYye3kXg64C2ibfk8omg3vKlsA"
        ) -> bool:
        """Generate quiz variants"""
        logger.info("🎯 Generating %d quiz variants in %s", variants, language)

        args = [
            "--language", language,
            "--variants", str(variants),
            "--output-dir", output_dir,
            "--results-sheet", results_sheet
        ]

        return self.run_script("quiz_generator_batch.py", args)

    def deploy_quizzes(self, language: Optional[str] = None, list_files: bool = False) -> bool:
        """Deploy quiz variants to Google Apps Script"""
        if list_files:
            logger.info("📁 Listing available quiz files")
            args = ["--list-files"]
        else:
            logger.info("🚀 Deploying quizzes{f' (%s)' if language else ''}", language)
            args = []

        if language:
            args.extend(["--language", language])

        return self.run_script("gas_deployer_batch.py", args)

    def send_emails(self, en_urls_file: str, sr_urls_file: str, recipients_file: str) -> bool:
        """Send bilingual email notifications"""
        logger.info("📧 Sending bilingual email notifications")

        # Check if files exist
        for file_path in [en_urls_file, sr_urls_file, recipients_file]:
            if not Path(file_path).exists():
                logger.error("File not found: %s", file_path)
                return False

        args = [en_urls_file, sr_urls_file, recipients_file]
        return self.run_script("email_notifier.py", args)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='AI Quiz System - Unified Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate quiz variants')
    gen_parser.add_argument('--language', '-l', choices=['ENG', 'SRB', 'BOTH'],
                           default='ENG', help='Language for quiz generation')
    gen_parser.add_argument('--variants', '-n', type=int, default=10,
                           help='Number of quiz variants to generate')
    gen_parser.add_argument('--output-dir', '-o', default='/tmp',
                           help='Output directory for generated files')
    gen_parser.add_argument(
        '--results-sheet',
        '-r',
        default='1ACSRHmuU_Jg1NuPsErYye3kXg64C2ibfk8omg3vKlsA',
        help='Google Sheets document ID to store results'
    )

    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy quizzes to Google Apps Script')
    deploy_parser.add_argument('--language', '-l', choices=['ENG', 'SRB'],
                              help='Deploy only specific language quizzes')
    deploy_parser.add_argument('--list-files', '-ls', action='store_true',
                              help='List available quiz files without deploying')

    # Email command
    email_parser = subparsers.add_parser('email', help='Send bilingual email notifications')
    email_parser.add_argument('en_urls_file', help='File containing English quiz URLs')
    email_parser.add_argument('sr_urls_file', help='File containing Serbian quiz URLs')
    email_parser.add_argument('recipients_file', help='File containing recipient email addresses')

    # Global options
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 1

    # Initialize orchestrator
    orchestrator = AIQuizOrchestrator()

    try:
        # Execute the requested command
        if args.command == 'generate':
            success = orchestrator.generate_quizzes(
                language=args.language,
                variants=args.variants,
                output_dir=args.output_dir,
                results_sheet=args.results_sheet
            )

        elif args.command == 'deploy':
            success = orchestrator.deploy_quizzes(
                language=args.language,
                list_files=args.list_files
            )

        elif args.command == 'email':
            success = orchestrator.send_emails(
                en_urls_file=args.en_urls_file,
                sr_urls_file=args.sr_urls_file,
                recipients_file=args.recipients_file
            )

        else:
            logger.error("Unknown command: %s", args.command)
            return 1

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("⏹️  Operation interrupted by user")
        return 1
    except RuntimeError as e:
        logger.error("❌ Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
