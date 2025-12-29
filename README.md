# AI Course Test Platform

A comprehensive platform for generating, deploying, and managing AI course tests
using Google Forms and Google Apps Script.

## Features

- **Test Generation**: Generate multiple test variants from JSON question pools
- **Multi-language Support**: English (EN) and Serbian (RS) languages
- **Google Forms Integration**: Deploy tests as Google Forms with auto-grading
- **Email Notifications**: Send bilingual email notifications with test URLs
- **Topic Analysis**: AI-powered analysis to detect redundant questions using GPT-4.1

## Project Structure

```
ai-course-test-platform/
├── main.py                    # Unified CLI entry point
├── test_generator.py          # Core test generation logic
├── test_generator_batch.py    # Batch generation of test variants
├── test_analyzer.py           # GPT-4.1 topic redundancy analyzer
├── gas_deployer.py            # Google Apps Script deployer
├── gas_deployer_batch.py      # Batch deployment
├── email_notifier.py          # Bilingual email notifications
├── QAPool/                    # Question pools organized by language
├── QATests/                   # Test configuration files
├── prompts/                   # Versioned LLM prompts
├── pyproject.toml             # uv project configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Google Cloud project with Forms API and Sheets API enabled
- OpenAI API key (for test analyzer)

### Setup

1. **Install dependencies with uv**
   ```bash
   uv sync
   ```

2. **Configure credentials**
   - Place your Google OAuth `credentials.json` in the project root
   - Set up environment variables in `.env`:
     ```
     OPENAI_API_KEY=your-openai-api-key
     ```

## Usage

### Using the Main CLI (Recommended)

The `main.py` script provides a unified interface for all operations.

#### Generate Test Variants

```bash
# Generate tests using config defaults (both languages, 10 variants each)
uv run python main.py generate QATests/l0-ai-citizen.json

# Generate 5 English variants only
uv run python main.py generate QATests/l0-ai-citizen.json --language en --variants 5

# Generate to custom output directory
uv run python main.py generate QATests/l0-ai-citizen.json --output-dir ./output
```

#### Deploy Tests

```bash
# Deploy all generated tests
uv run python main.py deploy

# Deploy only English tests
uv run python main.py deploy --language en

# List available test files without deploying
uv run python main.py deploy --list-files
```

#### Send Email Notifications

```bash
# Send bilingual emails with test URLs
uv run python main.py email en_urls_file.txt sr_urls_file.txt recipients.txt
```

### Using Individual Scripts

#### Test Generator Batch

```bash
# Generate test variants directly
uv run python test_generator_batch.py QATests/l0-ai-citizen.json

# With options
uv run python test_generator_batch.py QATests/l0-ai-citizen.json \
    --language en \
    --variants 5 \
    --output-dir /tmp/tests

# List existing test files
uv run python test_generator_batch.py QATests/l0-ai-citizen.json --list-files
```

#### Test Analyzer (Topic Redundancy)

Analyze tests for topic redundancy using GPT-4.1:

```bash
# Set API key
export OPENAI_API_KEY="your-key-here"

# Analyze test questions
uv run python test_analyzer.py \
    --test-config QATests/l0-ai-citizen.json \
    --materials-path /path/to/course-materials \
    --language en

# Use different model
uv run python test_analyzer.py \
    --test-config QATests/l0-ai-citizen.json \
    --model gpt-4-turbo
```

## Configuration

### Test Configuration (QATests/*.json)

```json
{
  "name": "AI Citizen",
  "language": "both",
  "results_sheet": "GOOGLE_SHEETS_ID",
  "content": {
    "/l0-ai-citizen/m1.json": 7,
    "/l0-ai-citizen/m2.json": 11,
    "/l0-ai-citizen/m3.json": 7
  },
  "variants": 10,
  "output-dir": "/tmp"
}
```

| Field           | Description                                                 |
|-----------------|-------------------------------------------------------------|
| `name`          | Test name displayed in Google Forms                         |
| `language`      | `"en"`, `"rs"`, or `"both"`                                 |
| `results_sheet` | Google Sheets ID for collecting responses                   |
| `content`       | Map of question file paths to number of questions to select |
| `variants`      | Number of test variants to generate                         |
| `output-dir`    | Directory for generated `.gs` files                         |

### Question Format (QAPool/*.json)

```json
[
  {
    "question": "Which scenario best represents Artificial Narrow Intelligence (ANI)?",
    "answers": [
      "A translation system that excels at converting text...",
      "An assistant that reaches human-level competence...",
      "A superintelligence that outperforms humans...",
      "A thermostat that uses a fixed rule..."
    ],
    "correct": "A translation system that excels at converting text..."
  }
]
```

## Generated Output

Test scripts are generated as Google Apps Script (`.gs`) files with the naming convention:

```
{Test Name} | {Date} | [{language}] | Variant {N}.gs
```

Example: `AI Citizen | 2024-12-24 | [en] | Variant 1.gs`

### Modifying the Analyzer Prompt

Edit `prompts/test_analyzer_prompt.md` to adjust how GPT-4.1 analyzes questions for redundancy.

