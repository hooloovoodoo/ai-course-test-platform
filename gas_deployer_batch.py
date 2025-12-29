"""
Batch Quiz Deployment Script

Deploys all generated quiz variants from /tmp to Google Apps Script
"""

import argparse
import logging
import glob
import sys
from pathlib import Path
from gas_deployer import GoogleAppsScriptDeployer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def deploy_all_quizzes(
    pattern: str = "/tmp/* | * | * | Variant *.gs", language: str = None
):
    """
    Deploy all quiz variants from /tmp directory

    Args:
        pattern: Glob pattern to find quiz files (default matches any quiz name)
        language: Optional language filter ("en", "rs", or None for all)

    Returns:
        List of deployed quiz information
    """

    # Find matching files
    quiz_files = glob.glob(pattern)

    # Filter by language if specified
    if language:
        language = language.lower()
        quiz_files = [f for f in quiz_files if f"[{language}]" in f]
        logger.info("🚀 Starting batch quiz deployment for %s quizzes...", language)
        if not quiz_files:
            logger.warning("⚠️  No %s quiz files found", language)
            return []
    else:
        logger.info("🚀 Starting batch quiz deployment for all languages...")

    if not quiz_files:
        logger.warning("⚠️  No quiz files found matching pattern: %s", pattern)
        return []

    logger.info("📄 Found %d quiz files to deploy", len(quiz_files))

    # Initialize deployer
    deployer = GoogleAppsScriptDeployer()

    # Authenticate
    if not deployer.authenticate_google():
        logger.error("❌ Authentication failed")
        return []

    # Deploy all quizzes
    deployed_quizzes = deployer.deploy_batch_quiz_scripts(pattern)

    if deployed_quizzes:
        logger.info("🎉 Successfully deployed %d quiz variants!", len(deployed_quizzes))

    return deployed_quizzes


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Deploy all generated quizes")

    parser.add_argument(
        "--pattern",
        default="/tmp/* | * | * | Variant *.gs",
        help="Glob pattern to find quiz files (default matches all quiz names)",
    )

    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "rs"],
        help="Deploy only quizzes for specific language (en or rs)",
    )

    parser.add_argument(
        "--list-files",
        "-ls",
        action="store_true",
        help="List available quiz files without deploying",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list_files:
        quiz_files = glob.glob(args.pattern)

        if args.language:
            quiz_files = [f for f in quiz_files if f"[{args.language.lower()}]" in f]

        if quiz_files:
            lang_msg = f" ({args.language} only)" if args.language else ""
            logger.info("📁 Found %d quiz files%s:", len(quiz_files), lang_msg)
            for file_path in sorted(quiz_files):
                file_name = Path(file_path).name
                file_size = Path(file_path).stat().st_size
                logger.info("   📄 %s (%d bytes)", file_name, file_size)
        else:
            lang_msg = f" for {args.language}" if args.language else ""
            logger.info("📁 No quiz files found%s", lang_msg)

    deploy_all_quizzes(args.pattern, args.language)


if __name__ == "__main__":
    sys.exit(main())
