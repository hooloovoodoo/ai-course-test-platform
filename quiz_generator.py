"""
Question Generator & Script Builder Module

This module handles:
1. Loading questions from JSON files
2. Converting JSON format to JavaScript-compatible structure
3. Randomly selecting questions for quizzes
4. Generating complete Google Apps Script code
5. Configurable quiz settings
"""

import json
import random
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Main class for generating quiz scripts from JSON question data"""

    def __init__(self,
                 name: str,
                 language: str,
                 results_sheet: str,
                 description: str = "To AI or not to AI, that is the question",
                 points_per_question: int = 1,
                 confirmation_message: str = "Hvala što ste učestvovali u kvizu! / Thanks for taking the quiz!"):
        """
        Initialize the quiz generator

        Args:
            name: Quiz name/title (e.g., "AI Citizen")
            language: ISO 3166 language code ("en", "rs", or "both")
            results_sheet: Google Sheets document ID to store results
            description: Quiz description (optional)
            points_per_question: Points awarded per question (optional)
            confirmation_message: Message shown after completion (optional)
        """
        self.name = name
        self.language = language.lower()
        self.results_sheet = results_sheet
        self.description = description
        self.points_per_question = points_per_question
        self.confirmation_message = confirmation_message

        # Title will be set dynamically with language tag
        self.title = name

    def get_file_configs_from_content(
        self, content_config: Dict[str, int], language: str) -> List[Dict[str, Any]]:
        """
        Build file configurations from content config and language

        Args:
            content_config: Dictionary mapping relative paths to question counts
                           e.g., {"/l0-ai-citizen/m1.json": 7, ...}
            language: ISO 3166 language code ("en" or "rs")

        Returns:
            List of file configurations with full paths and question counts
        """
        language = language.lower()

        # Validate language code
        if language not in ["en", "rs"]:
            raise ValueError(f"Unsupported language: {language}. Use 'en' or 'rs'")

        file_configs = []

        for relative_path, count in content_config.items():
            # Build full path: QAPool/{language}{relative_path}
            full_path = f"QAPool/{language}{relative_path}"
            file_configs.append({
                'path': full_path,
                'count': count
            })

        return file_configs

    def load_questions_from_multiple_files(
        self,
        file_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Load and validate questions from multiple JSON files with specific counts

        Args:
            file_configs: List of dicts with 'path' and 'count' keys
                         e.g., [{'path': 'l0/m1.json', 'count': 10}, ...]

        Returns:
            List of validated question dictionaries from all files

        Raises:
            FileNotFoundError: If any JSON file doesn't exist
            ValueError: If JSON format is invalid or insufficient questions
        """
        all_questions = []

        for config in file_configs:
            file_path = config['path']
            required_count = config['count']

            logger.info("Loading %d questions from %s",
            required_count, file_path)
            file_questions = self.load_questions(file_path)

            if len(file_questions) < required_count:
                raise ValueError(
                    f"File {file_path} has only {len(file_questions)} questions, "
                    f"but {required_count} required"
                )

            selected_questions = random.sample(file_questions, required_count)
            all_questions.extend(selected_questions)

            logger.info("Selected %d questions from %s",
                        len(selected_questions), file_path)

        logger.info("Total questions loaded: %d", len(all_questions))
        return all_questions

    def load_questions(
        self,
        json_path: str) -> List[Dict[str, Any]]:
        """
        Load and validate questions from JSON file

        Args:
            json_path: Path to the JSON file containing questions

        Returns:
            List of validated question dictionaries

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON format is invalid
        """
        try:
            json_file = Path(json_path)
            if not json_file.exists():
                raise FileNotFoundError(f"Question file not found: {json_path}")

            with open(json_file, 'r', encoding='utf-8') as f:
                questions = json.load(f)

            if not isinstance(questions, list):
                raise ValueError("JSON file must contain a list of questions")

            # Validate question structure
            validated_questions = []
            for i, question in enumerate(questions):
                if not self._validate_question(question, i):
                    continue
                validated_questions.append(question)

            logger.info("Loaded %d valid questions from %s",
            len(validated_questions), json_path)
            return validated_questions

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {json_path}: {e}") from e

        except RuntimeError as e:
            logger.error("Error loading questions: %s", e)
            raise

    def _validate_question(
        self,
        question: Dict[str, Any],
        index: int) -> bool:
        """
        Validate individual question structure

        Args:
            question: Question dictionary to validate
            index: Question index for error reporting

        Returns:
            True if question is valid, False otherwise
        """
        required_fields = ['question', 'answers', 'correct']

        for field in required_fields:
            if field not in question:
                logger.warning(
                    "Question %d: Missing required field '%s', skipping",
                    index, field)
                return False

        if not isinstance(question['answers'], list) or len(question['answers']) != 4:
            logger.warning(
                "Question %d: 'answers' must be a list of 4 options, skipping",
                index)
            return False

        if question['correct'] not in question['answers']:
            logger.warning(
                "Question %d: 'correct' answer not found in 'answers', skipping",
                index)
            return False

        return True

    def convert_format(
        self,
        questions: List[Dict[str, Any]],
        shuffle_choices: bool = True) -> List[Dict[str, Any]]:
        """
        Convert JSON question format to JavaScript-compatible structure

        Args:
            questions: List of questions in JSON format
            shuffle_choices: Whether to randomize the order of answer choices

        Returns:
            List of questions in JS-compatible format
        """
        js_questions = []

        for question in questions:
            choices = question['answers'].copy()
            correct_answer = question['correct']

            if shuffle_choices:
                # Shuffle the choices and find new correct index
                random.shuffle(choices)
                correct_index = choices.index(correct_answer)
            else:
                # Keep original order
                correct_index = choices.index(correct_answer)

            # Add "I don't know" option as the last choice (after shuffling)
            if self.language == "ENG":
                choices.append("I don't know")
            else:  # SRB
                choices.append("Ne znam")

            js_question = {
                'question': question['question'],
                'choices': choices,
                'correct': correct_index
            }

            js_questions.append(js_question)

        logger.info("Converted %d questions to JS format (shuffle_choices=%s)",
                    len(js_questions), shuffle_choices)
        return js_questions

    def select_random_questions(
        self,
        questions: List[Dict[str, Any]],
        count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Randomly select questions from the pool

        Args:
            questions: List of available questions
            count: Number of questions to select (defaults to config.question_count)

        Returns:
            List of randomly selected questions

        Raises:
            ValueError: If requested count exceeds available questions
        """
        if count is None:
            count = 25  # Total questions: 7 + 11 + 7

        if count > len(questions):
            raise ValueError(f"Requested {count} questions but only {len(questions)} available")

        selected = random.sample(questions, count)
        logger.info("Selected %d random questions", len(selected))
        return selected

    def generate_script(
        self,
        questions: List[Dict[str, Any]]) -> str:
        """
        Generate complete Google Apps Script code with embedded questions

        Args:
            questions: List of questions in JS format

        Returns:
            Complete Google Apps Script code as string
        """
        # Convert questions to JavaScript array format
        questions_js = self._format_questions_for_js(questions)

        script_template = f'''/**
 * Creates an AI Knowledge Quiz with {len(questions)} questions
 * - Autograded multiple choice questions with {self.points_per_question} point(s) each
 * - Immediate feedback showing correct answers and score
 * - Email notification with PASS/FAIL result (80% threshold)
 * - Centralized response collection in Google Sheets: {self.results_sheet}
 */
function createRandomAIQuiz() {{
  const questionsPool = {questions_js};

  // Shuffle and pick {len(questions)} questions
  const selectedQuestions = shuffleArray(questionsPool).slice(0, {len(questions)});

  // Create the quiz form
  const form = FormApp.create('{self._escape_js_string(self.title)}')
    .setIsQuiz(true)
    .setCollectEmail(true)
    .setShowLinkToRespondAgain(false);

  form.setTitle('{self._escape_js_string(self.title)}');
  form.setDescription('{self._escape_js_string(self.description)}');

  // Link form to Google Sheets for centralized response collection
  try {{
    const spreadsheetId = '{self.results_sheet}';
    form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);
    Logger.log(`✅ Form linked to Google Sheets: ${{spreadsheetId}}`);
  }} catch (error) {{
    Logger.log(`⚠️  Could not link to spreadsheet: ${{error.message}}`);
    Logger.log('Form will store responses in its own response sheet');
  }}

  // Optional settings for better UX
  form.setPublishingSummary(false);
  form.setLimitOneResponsePerUser(true);
  form.setConfirmationMessage('{self._escape_js_string(self.confirmation_message)}');

  // Helper function to add a fully-configured MC question
  const addMCQuestion = (questionData) => {{
    const item = form.addMultipleChoiceItem();
    item.setTitle(questionData.question)
        .setPoints({self.points_per_question})
        .setRequired(true);

    // Build choices with exactly one correct answer
    const choices = questionData.choices.map((choice, index) =>
      item.createChoice(choice, index === questionData.correct)
    );
    item.setChoices(choices);

    // Optional feedback for immediate learning
    const fbCorrect = FormApp.createFeedback().setText('Correct! ✅').build();
    const fbIncorrect = FormApp.createFeedback().setText('Review this topic.').build();
    item.setFeedbackForCorrect(fbCorrect);
    item.setFeedbackForIncorrect(fbIncorrect);

    return item;
  }};

  // Add all selected questions to the form
  selectedQuestions.forEach(questionData => {{
    addMCQuestion(questionData);
  }});

  // Clean up any existing triggers for this handler to avoid duplicates
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'onFormSubmit')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));

  // Create the form submission trigger for PASS/FAIL email logic
  ScriptApp.newTrigger('onFormSubmit')
    .forForm(form)
    .onFormSubmit()
    .create();

  const totalPoints = selectedQuestions.length * {self.points_per_question};
  const passingScore = Math.ceil(totalPoints * 0.8);

  Logger.log('=== QUIZ CREATED SUCCESSFULLY ===');
  Logger.log(`Questions: ${{selectedQuestions.length}}`);
  Logger.log(`Points per question: {self.points_per_question}`);
  Logger.log(`Total possible points: ${{totalPoints}}`);
  Logger.log(`Passing score (80%): ${{passingScore}} points`);
  Logger.log('');
  Logger.log('Form URLs:');
  Logger.log('Edit form: ' + form.getEditUrl());
  Logger.log('Live quiz: ' + form.getPublishedUrl());
  Logger.log('');
  Logger.log('✅ Trigger installed for PASS/FAIL email notifications');

  return {{
    publishedUrl: form.getPublishedUrl(),
    editUrl: form.getEditUrl(),
    formId: form.getId()
  }};
}}

// Helper function to shuffle array
function shuffleArray(array) {{
  let currentIndex = array.length, temporaryValue, randomIndex;
  while (0 !== currentIndex) {{
    randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex--;
    // Swap
    temporaryValue = array[currentIndex];
    array[currentIndex] = array[randomIndex];
    array[randomIndex] = temporaryValue;
  }}
  return array;
}}

/**
 * On submit: compute score by comparing responses to marked correct choices
 * for all Multiple Choice items, then email PASS/FAIL at 80%.
 */
function onFormSubmit(e) {{
  const form = e.source;
  const response = e.response;

  const email = response.getRespondentEmail();
  if (!email) return;

  const mcItems = form.getItems(FormApp.ItemType.MULTIPLE_CHOICE);
  let totalPoints = 0;
  let earnedPoints = 0;

  mcItems.forEach(item => {{
    const mci = item.asMultipleChoiceItem();
    const points = mci.getPoints() || 0;
    totalPoints += points;

    const ir = response.getResponseForItem(item);
    const answer = ir ? ir.getResponse() : null;

    const correctChoice = mci.getChoices().find(c => c.isCorrectAnswer());
    const correctValue = correctChoice ? correctChoice.getValue() : null;

    if (answer !== null && correctValue !== null && answer === correctValue) {{
      earnedPoints += points;
    }}
  }});

  const pct = totalPoints > 0 ? (earnedPoints / totalPoints) * 100 : 0;
  const passed = pct >= 80;

  const subject = `{self.name}: ${{Math.round(pct)}}% — ${{passed ? 'PASS ✅' : 'FAIL ❌'}}`;

  const HERO_IMAGE_URL = `https://cdn.haip.hooloovoo.rs/${{passed ? "pass" : "fail"}}.jpg`;
  const heroBlob = UrlFetchApp.fetch(HERO_IMAGE_URL, {{ muteHttpExceptions: true }}).getBlob().setName("hero.jpg");

  const textBody = `Hvala što ste učestvovali u kvizu! / Thanks for taking the quiz!

🎯: ${{earnedPoints}} / ${{totalPoints}} (${{pct.toFixed(1)}}%)
🏁: ${{passed ? 'PASS ✅' : 'FAIL ❌'}}`;

  const htmlBody = `<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f6f6f6;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f6f6;">
      <tr>
        <td align="center" style="padding:24px;">
          <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;background:#ffffff;border-radius:8px;overflow:hidden;">
            <tr>
              <td align="center" style="padding:24px;">
                <h1 style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:20px;line-height:1.3;color:#222;">
                  {self.name}
                </h1>
                <p style="font-family:Arial,Helvetica,sans-serif;color:#555;margin:12px 0 24px;">
                  Hvala što ste učestvovali u kvizu! / Thanks for taking the quiz!
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 24px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eee;border-radius:8px;">
                  <tr>
                    <td style="padding:16px 20px;font-family:Arial,Helvetica,sans-serif;color:#333;">
                      <div style="font-size:16px;margin-bottom:6px;">🎯: <strong>${{earnedPoints}} / ${{totalPoints}}</strong> (${{pct.toFixed(1)}}%)</div>
                      <div style="font-size:16px;">🏁: <strong>${{passed ? "PASS ✅" : "FAIL ❌"}}</strong></div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- HERO as CID (no hosting needed) -->
            <tr>
              <td align="center" style="padding:0 24px 24px;">
                <img src="cid:hero-cid" width="600" height="200" alt="Hero"
                     style="display:block;border:0;outline:0;text-decoration:none;margin:0 auto;max-width:100%;height:auto;">
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 24px;">
                <p style="font-family:Arial,Helvetica,sans-serif;color:#666;margin:0;">
                  Ova poruka je automatski poslata nakon podnošenja Google Forme.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`;

  MailApp.sendEmail({{
    to: email,
    subject: subject,
    body: textBody,
    htmlBody: htmlBody,
    inlineImages: {{
      "hero-cid": heroBlob
    }},
    name: "{self.name} Quiz"
  }});


}}'''

        logger.info("Generated Google Apps Script code")
        return script_template

    def _escape_js_string(
        self,
        text: str) -> str:
        """Escape special characters for JavaScript strings (double-quoted)"""
        return text.replace(
            '\\', '\\\\').replace(
                '"', '\\"').replace(
                    '\n', '\\n').replace(
                        '\r', '\\r')

    def _format_questions_for_js(
        self,
        questions: List[Dict[str, Any]]) -> str:
        """
        Format questions as JavaScript array string

        Args:
            questions: List of questions in JS format

        Returns:
            JavaScript array string representation
        """
        js_array = "[\n"

        for i, q in enumerate(questions):
            question_text = self._escape_js_string(q['question'])
            choices = [self._escape_js_string(choice) for choice in q['choices']]

            js_array += f'''    {{
      question: "{question_text}",
      choices: {json.dumps(choices)},
      correct: {q['correct']}
    }}'''

            if i < len(questions) - 1:
                js_array += ","
            js_array += "\n"

        js_array += "  ]"
        return js_array

    def save_script(
        self,
        script_content: str,
        output_path: str) -> None:
        """
        Save generated script to file

        Args:
            script_content: Generated Google Apps Script code
            output_path: Path where to save the script file
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(script_content)

            logger.info("Script saved to %s", output_path)

        except RuntimeError as e:
            logger.error("Error saving script: %s", e)
            raise

    def generate_quiz_from_multiple_files(
        self,
        file_configs: List[Dict[str, Any]],
        output_path: str) -> str:
        """
        Complete workflow: Load questions from multiple JSONs, generate script, save to file

        Args:
            file_configs: List of dicts with 'path' and 'count' keys
                         e.g., [{'path': 'QAPool/en/l0-ai-citizen/m1.json', 'count': 10}, ...]
            output_path: Path to save generated script

        Returns:
            Generated script content
        """
        try:
            # Update title with language tag
            original_title = self.title
            language_tag = f"[{self.language}]"

            # Set title with language tag
            self.title = f"{original_title} {language_tag}"

            # Load questions from multiple files
            all_questions = self.load_questions_from_multiple_files(file_configs)

            # Convert to JS format
            js_questions = self.convert_format(all_questions)

            # Shuffle all questions together
            random.shuffle(js_questions)

            # Generate script
            script_content = self.generate_script(js_questions)

            # Save to file
            self.save_script(script_content, output_path)

            total_questions = sum(config['count'] for config in file_configs)
            logger.info(
                "Successfully generated %s quiz script with %d questions from %d files",
                self.language,
                total_questions,
                len(file_configs))

            # Restore original title
            self.title = original_title

            return script_content

        except RuntimeError as e:
            logger.error("Error in multi-file quiz generation workflow: %s", e)
            raise

    def generate_quiz_from_json(
        self,
        json_path: str,
        output_path: str,
        question_count: Optional[int] = None) -> str:
        """
        Complete workflow: Load JSON, generate script, and save to file

        Args:
            json_path: Path to JSON question file
            output_path: Path to save generated script
            question_count: Number of questions to select (optional)

        Returns:
            Generated script content
        """
        try:
            # Update title with language
            original_title = self.title
            language_tag = f"[{self.language}]"

            # Set title with language tag only
            self.title = f"{original_title} {language_tag}"

            # Load and validate questions
            questions = self.load_questions(json_path)

            # Convert to JS format
            js_questions = self.convert_format(questions)

            # Select random subset
            selected_questions = self.select_random_questions(js_questions, question_count)

            # Generate script
            script_content = self.generate_script(selected_questions)

            # Save to file
            self.save_script(script_content, output_path)

            logger.info(
                "Successfully generated %s quiz script with %d questions",
                self.language,
                len(selected_questions))

            # Restore original title
            self.title = original_title

            return script_content

        except RuntimeError as e:
            logger.error("Error in quiz generation workflow: %s", e)
            raise

    def generate_quiz_for_language(
        self,
        content_config: Dict[str, int],
        language: str,
        output_path: str = None,
        variant_number: Optional[int] = None) -> str:
        """
        Generate quiz using content configuration for the specified language

        Args:
            content_config: Dictionary mapping relative paths to question counts
            language: ISO 3166 language code ("en" or "rs")
            output_path: Path to save generated script (optional)
            variant_number: Optional variant number to include in title

        Returns:
            Generated script content
        """
        # Update language
        self.language = language.lower()

        # Get file configurations for the language
        file_configs = self.get_file_configs_from_content(content_config, language)

        # Generate default output path if not provided
        if output_path is None:
            lang_suffix = language.lower()
            if variant_number is not None:
                output_path = f"generated_quiz_{lang_suffix}_variant_{variant_number}.gs"
            else:
                output_path = f"generated_quiz_{lang_suffix}.gs"

        return self.generate_quiz_from_multiple_files(file_configs, output_path)


# Example usage and testing
if __name__ == "__main__":
    # Example content configuration
    content_config = {
        "/l0-ai-citizen/m1.json": 7,
        "/l0-ai-citizen/m2.json": 11,
        "/l0-ai-citizen/m3.json": 7
    }

    # Initialize generator with required parameters
    # NOTE: Replace with your actual Google Sheets ID
    generator = QuestionGenerator(
        name="AI Citizen",
        language="en",
        results_sheet="YOUR_GOOGLE_SHEETS_ID_HERE"
    )

    # Test both languages
    try:
        # Generate English quiz
        print("Generating English quiz...")
        eng_script = generator.generate_quiz_for_language(
            content_config=content_config,
            language="en",
            output_path="generated_quiz_eng.gs",
            variant_number=1
        )
        print("English quiz generation completed successfully!")
        print(f"Script length: {len(eng_script)} characters")

        # Generate Serbian quiz
        print("\nGenerating Serbian quiz...")
        srb_script = generator.generate_quiz_for_language(
            content_config=content_config,
            language="rs",
            output_path="generated_quiz_srb.gs",
            variant_number=1
        )
        print("Serbian quiz generation completed successfully!")
        print(f"Script length: {len(srb_script)} characters")

    except RuntimeError as e:
        print("Error: %s", e)
