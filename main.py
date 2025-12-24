#!/usr/bin/env python3
"""
AI Test System - Main Entry Point

This script provides a unified interface for the complete AI test:
1. Generate test variants from JSON config files (test_generator_batch.py)
2. Deploy tests to Google Apps Script (gas_deployer_batch.py)
3. Send bilingual email notifications (email_notifier.py)

Usage Examples:
    # Generate test variants from config file (uses config defaults)
    python main.py generate QATests/l0-ai-citizen.json

    # Generate with overrides (5 English variants only)
    python main.py generate QATests/l0-ai-citizen.json --language en --variants 5

    # Generate AI Coder test
    python main.py generate QATests/l1-ai-coder.json

    # Deploy all English tests
    python main.py deploy --language en

    # Send emails with test URLs
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


class AITestOrchestrator:
    """Main orchestrator for the AI test system"""

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

        # Default config directory
        self.config_dir = self.base_dir / "QATests"

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

    def generate_tests(
        self,
        config_file: str,
        language: str = None,
        variants: int = None,
        output_dir: str = None
        ) -> bool:
        """Generate test variants from configuration file"""
        config_path = self.base_dir / config_file

        if not config_path.exists():
            logger.error("Configuration file not found: %s", config_path)
            return False

        logger.info("🎯 Generating test variants from config: %s", config_file)

        args = [str(config_path)]

        # Add optional overrides
        if language:
            args.extend(["--language", language])
        if variants:
            args.extend(["--variants", str(variants)])
        if output_dir:
            args.extend(["--output-dir", output_dir])

        return self.run_script("test_generator_batch.py", args)

    def deploy_tests(self, language: Optional[str] = None, list_files: bool = False) -> bool:
        """Deploy test variants to Google Apps Script"""
        if list_files:
            logger.info("📁 Listing available test files")
            args = ["--list-files"]
        else:
            logger.info("🚀 Deploying tests{f' (%s)' if language else ''}", language)
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
        description='AI Test System - Unified Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate test variants')
    gen_parser.add_argument('config', help='Path to configuration file (e.g., QATests/l0-ai-citizen.json)')
    gen_parser.add_argument('--language', '-l', choices=['en', 'rs'],
                           help='Override language from config (en or rs)')
    gen_parser.add_argument('--variants', '-n', type=int,
                           help='Override number of test variants from config')
    gen_parser.add_argument('--output-dir', '-o',
                           help='Override output directory from config')

    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy tests to Google Apps Script')
    deploy_parser.add_argument('--language', '-l', choices=['en', 'rs'],
                              help='Deploy only specific language tests (en or rs)')
    deploy_parser.add_argument('--list-files', '-ls', action='store_true',
                              help='List available test files without deploying')

    # Email command
    email_parser = subparsers.add_parser('email', help='Send bilingual email notifications')
    email_parser.add_argument('en_urls_file', help='File containing English test URLs')
    email_parser.add_argument('sr_urls_file', help='File containing Serbian test URLs')
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
    orchestrator = AITestOrchestrator()

    try:
        # Execute the requested command
        if args.command == 'generate':
            success = orchestrator.generate_tests(
                config_file=args.config,
                language=args.language,
                variants=args.variants,
                output_dir=args.output_dir
            )

        elif args.command == 'deploy':
            success = orchestrator.deploy_tests(
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
