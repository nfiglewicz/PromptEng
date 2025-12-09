import os
import json
import base64
from PIL import Image
from io import BytesIO
import re
import requests # For downloading image from URL if needed
from typing import Type
import argparse # Import argparse

# Langchain and Google specific imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage

from pydantic import BaseModel, Field


FEEDBACK_MODEL = "gemini-2.5-flash-preview-05-20" # Make sure this model is available and supports vision for aesthetics

# Attempt to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Prompt Templates (Keep them as they are) ---
CODE_QUALITY_PROMPT_TEMPLATE = """
**You are:** A highly experienced Senior Software Engineer, renowned for your pragmatic approach and deep understanding of full-stack development best practices. You appreciate elegant solutions, even when built under pressure. 

**Your Task:** You will be given the concatenated source code (plain text) of a project developed during a 3-hour programming contest by a team of 5. The code is separated into Frontend (HTML, JavaScript, CSS) and Backend (Python with Flask) sections below. 

Your goal is to evaluate the **Frontend** and **Backend** code **separately** based on code quality and practical application of software engineering principles *within the context of the contest*. 

**For *each* section (Frontend and Backend):** 1. **Assign a Score:** Provide an overall score from 1 to 5. 
* **1:** Very poor, significant issues even considering the time limit. 
* **2:** Below average, functional but messy or confusing. 
* **3:** Average, gets the job done, some good parts, some areas for quick improvement. 
* **4:** Good, clear structure and demonstrates good practices for rapid development.
* **5:** Excellent, exceptionally clean, well-structured, and demonstrates strong, efficient coding practices *achievable within the 3-hour timeframe*. This represents the best one might expect under these constraints, not necessarily production-ready perfection. 
2. **Provide a Rationale:** Write a brief rationale (strictly **maximum 100 words**) explaining the score. Maintain a professional yet **witty and insightful** tone – the humor should highlight the technical points, not obscure them. 

**Overall Evaluation:** 1. **Calculate Average Score:** Compute the average of the Frontend and Backend scores: `(Frontend Score + Backend Score) / 2`. 
2. **Create a Title:** Devise a short, humorous, and fitting title (3-5 words) for the overall evaluation (e.g., "Surprisingly Slick Speedrun", "Functional Frenzy", "Could Use More Duct Tape"). 

**Important Context for Evaluation:**
* **Time Constraint:** This was a 3-hour contest. Evaluate based on what's realistically achievable in that time by a 5-person team. Prioritize clarity, basic structure, and functionality over complex patterns or optimizations.
* **Hardcoded Values:** The requirements mandated hardcoding certain URLs and City names. **Do not penalize the code for this specific aspect.**
* **Testing Evaluation:** The simple presence or absence of automated tests should not directly determine the score (i.e., don't automatically deduct points if no tests are present). However, **if tests *are* provided**, their **quality** (e.g., relevance, clarity, effectiveness, maintainability) **should be considered** as part of the overall code quality assessment for the relevant section (Frontend/Backend). Well-written, meaningful tests can positively influence the score, reflecting good practices. Conversely, poorly written or trivial tests (if present) might indicate a misunderstanding or detract from the overall impression of craftsmanship. If no tests are provided, evaluate solely based on the application code.

Output Structure: Please structure your response in JSON format:
{{
  "frontend_evaluation": {{
    "score": "[1-5]",
    "rationale": "[Your witty, insightful rationale - max 100 words]"
  }},
  "backend_evaluation": {{
    "score": "[1-5]",
    "rationale": "[Your witty, insightful rationale - max 100 words]"
  }},
  "overall": {{
    "title": "[Your humorous 3-5 word title]",
    "average_score": "[Calculated Average]"
  }}
}}
---

**Language:**
The whole evaluation, score, rationale, etc, shall be written in **polish**.

**Now, please evaluate the code provided below:**

**Backend Code**
-------------------------
{backend_code}

**Frontend Code**
-------------------------
{frontend_code}
"""

FRONTEND_AESTHETICS_PROMPT_TEMPLATE = """
**You are:** A highly experienced UI Designer, renowned for your pragmatic approach and deep understanding of UX development and experience best practices. You appreciate elegant solutions, even when built under pressure. 

**Your Task:**
You will be given a **screenshot of the frontend**. You may also receive the concatenated code for context *only* if needed to understand *how* a visual element functions, but your evaluation must focus *solely* on the visual result and user experience depicted in the screenshot, **not** the code's quality or structure. Your goal is to evaluate the **User Experience (UX) and visual aesthetics of the Frontend** depicted in the screenshot, considering standard usability heuristics and visual design principles, adapted for the rapid development context. 

To perform the evaluation: 
1. **Assign a Score:** Provide an overall score from 1 to 5. 
* **1:** Very poor, significant usability or visual issues even considering the time limit. 
* **2:** Below average, functional but visually messy, confusing layout, or hinders intuitive use. 
* **3:** Average, gets the core task done, some good parts, some areas for quick visual/UX improvement. 
* **4:** Good, demonstrates good foundational UX/UI practices suitable for rapid development; clear and mostly intuitive. 
* **5:** Excellent, exceptionally clear, usable, and visually coherent; demonstrates strong, efficient *design choices* achievable within the 3-hour timeframe. This represents the best one might expect under these constraints, not necessarily production-ready perfection. 
2. **Provide a Rationale:** Write a brief rationale (strictly **maximum 100 words**) explaining the score. Maintain a professional yet **witty and insightful** tone – the humor should highlight the technical points, not obscure them. 
3. **Create a Title:** Devise a short, humorous, and fitting title (3-5 words) for the overall evaluation (e.g., "Surprisingly Slick Speedrun", "Functional Frenzy", "Could Use More Duct Tape"). 

**Important Context for Evaluation:** * **Time Constraint:** This was a 3-hour contest. Evaluate based on what's realistically achievable in that time by a 5-person team. Prioritize core functionality and basic clarity. 
* **Focus:** Focus on **clarity, navigability, task completion ease, visual hierarchy, and overall coherence** achievable under pressure, rather than pixel-perfection or advanced features. 
* **Code Quality:** Do **not** consider the quality of the underlying code. Evaluate *only* the UX and visual aesthetics presented to the user via the screenshot. 

Output Structure: Please structure your response in JSON format:
{{
    "score": "[1-5]",
    "rationale": "[Your witty, insightful rationale - max 100 words]",
    "title": "[Your humorous 3-5 word title]"
}},

**Output Language:** The entire evaluation output (including the rationale, title, and the content for the labels "Score", "Rationale", "Title") must be written in **Polish**. 

**Now, please evaluate the user experience and aesthetics based on the screenshot and context provided below:** **Frontend Code Context (for reference only if needed to understand visual elements):**
-------------------------
{frontend_code}

**(The primary evaluation should be based on the provided screenshot image.)**
"""

IMAGE_PROMPT_GENERATION_META_PROMPT_TEMPLATE = """
You are an AI assistant that crafts vivid text-to-image prompts.
Based on the following software evaluation feedback:
Evaluation Type: {evaluation_type}
Score: {score}/5
Rationale (Keywords/Summary): {rationale_summary}

Generate a concise (maximum 40 words) and artistic text prompt suitable for a text-to-image model like Imagen. The image should be a symbolic digital art illustration that visually captures the essence of this feedback in a witty and insightful style. Focus on metaphors and abstract concepts related to the evaluation type ({evaluation_type_hint}) and the score's meaning. The image should be visually appealing and thought-provoking.

Image Prompt:
"""

# --- Helper Functions ---
def read_file_content(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Modified to raise the specific error rather than a generic string
        raise FileNotFoundError(f"Error: File not found at {file_path}")
    except Exception as e:
        # Consider re-raising with more context or logging
        raise Exception(f"Error reading file {file_path}: {e}")

def encode_image_to_base64(image_path: str):
    try:
        with Image.open(image_path) as img:
            img_format = img.format or "PNG"
            if img.mode == 'RGBA' and img_format.lower() == 'jpeg':
                img = img.convert('RGB')
            buffered = BytesIO()
            img.save(buffered, format=img_format)
            img_byte = buffered.getvalue()
            encoded_string = base64.b64encode(img_byte).decode('utf-8')
            return f"data:image/{img_format.lower()};base64,{encoded_string}", None
    except FileNotFoundError:
        return None, f"Error: Image file not found at {image_path}"
    except Exception as e:
        return None, f"Error processing image {image_path}: {e}"


def parse_code_quality_output(text_output: str):
    cleaned_text = text_output

    match = re.search(r"```json\s*([\s\S]*?)\s*```", cleaned_text, re.DOTALL)
    if match:
        cleaned_text = match.group(1)
    else:
        if cleaned_text.strip().startswith("{") and cleaned_text.strip().endswith("}"):
            cleaned_text = cleaned_text.strip()
        else:
            cleaned_text = cleaned_text.removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(cleaned_text)
        results = {
            "frontend_score": None, "frontend_rationale": "N/A",
            "backend_score": None, "backend_rationale": "N/A",
            "overall_title": "N/A", "overall_average_score": None
        }

        if "frontend_evaluation" in data:
            fe = data["frontend_evaluation"]
            score_fe = fe.get("score")
            try:
                results["frontend_score"] = int(score_fe) if score_fe is not None else None
            except (ValueError, TypeError):
                results["frontend_score"] = float(score_fe) if score_fe is not None else None
            results["frontend_rationale"] = fe.get("rationale", "N/A")

        if "backend_evaluation" in data:
            be = data["backend_evaluation"]
            score_be = be.get("score")
            try:
                results["backend_score"] = int(score_be) if score_be is not None else None
            except (ValueError, TypeError):
                results["backend_score"] = float(score_be) if score_be is not None else None
            results["backend_rationale"] = be.get("rationale", "N/A")

        if "overall" in data:
            overall = data["overall"]
            results["overall_title"] = overall.get("title", "N/A")
            avg_score = overall.get("average_score")
            try:
                results["overall_average_score"] = float(avg_score) if avg_score is not None else None
            except (ValueError, TypeError):
                results["overall_average_score"] = None

        return results
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for code quality: {e}. Cleaned text snippet: {cleaned_text[:500]}")
        return {
            "frontend_score": None, "frontend_rationale": "Parsing Error",
            "backend_score": None, "backend_rationale": "Parsing Error",
            "overall_title": "Parsing Error", "overall_average_score": None
        }
    except Exception as e:
        print(f"An unexpected error occurred in parse_code_quality_output: {e}. Text snippet: {text_output[:500]}")
        return {
            "frontend_score": None, "frontend_rationale": "Unexpected Error",
            "backend_score": None, "backend_rationale": "Unexpected Error",
            "overall_title": "Unexpected Error", "overall_average_score": None
        }


def parse_aesthetics_output(text_output: str):
    results = {"score": None, "rationale": "N/A", "title": "N/A"}
    cleaned_text = text_output.strip()
    match = re.search(r"```json\s*([\s\S]*?)\s*```", cleaned_text, re.DOTALL)
    if match:
        json_string = match.group(1).strip()
    else:
        match_simple_ticks = re.search(r"```\s*([\s\S]*?)\s*```", cleaned_text, re.DOTALL)
        if match_simple_ticks:
            json_string = match_simple_ticks.group(1).strip()
        else:
            json_string = cleaned_text
    try:
        data = json.loads(json_string)
        score_val = data.get("score")
        if score_val is not None:
            try:
                results["score"] = int(score_val)
            except (ValueError, TypeError):
                print(f"Warning: Could not convert aesthetics score '{score_val}' to int. Leaving as None.")
                results["score"] = None
        results["rationale"] = data.get("rationale", "N/A").strip()
        results["title"] = data.get("title", "N/A").strip()
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for aesthetics: {e}. Problematic string part: '{json_string[:500]}'")
    except Exception as e:
        print(f"An unexpected error occurred during aesthetics parsing: {e}. Original text: {text_output[:500]}")
    return results


# --- Image Generation Functions ---
def generate_image_prompt_from_feedback(
        evaluation_type: str,
        score: int,
        rationale_summary: str,
        llm_text_model: ChatGoogleGenerativeAI
) -> str:
    if score is None or not rationale_summary or rationale_summary == "N/A":
        return "Error: Insufficient data to generate image prompt."

    evaluation_type_hint_map = {
        "Frontend Code Quality": "code structure, clarity, efficiency, user interface logic",
        "Backend Code Quality": "server-side logic, database interaction, API design, robustness",
        "Frontend Aesthetics & UX": "user interface design, visual appeal, ease of use, user experience flow"
    }
    evaluation_type_hint = evaluation_type_hint_map.get(evaluation_type, "software project aspect")

    meta_prompt = IMAGE_PROMPT_GENERATION_META_PROMPT_TEMPLATE.format(
        evaluation_type=evaluation_type,
        score=score,
        rationale_summary=rationale_summary,
        evaluation_type_hint=evaluation_type_hint
    )

    try:
        response = llm_text_model.invoke([HumanMessage(content=meta_prompt)])
        image_prompt_text = response.content.replace("Image Prompt:", "").strip()
        return image_prompt_text
    except Exception as e:
        print(f"[ImagePromptGen] Error generating image prompt: {e}")
        return f"Error generating image prompt: {e}"


def save_image_from_url(image_url: str, filename: str):
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        print(f"[ImageSave] Image successfully saved from URL to: {filename}")
    except Exception as e:
        print(f"[ImageSave] Error saving image from URL {image_url}: {e}")


# --- Langchain Tool Definitions  ---

class CodeQualityInput(BaseModel):
    backend_code_path: str = Field(description="Path to backend code file")
    frontend_code_path: str = Field(description="Path to frontend code file")

class CodeQualityTool(BaseTool):
    name: str = "CodeQualityEvaluator"
    description: str = "Evaluates code quality and generates illustrative images. Input: paths to backend and frontend code files."
    args_schema: Type[CodeQualityInput] = CodeQualityInput
    google_api_key: str

    def _run(self, backend_code_path: str, frontend_code_path: str) -> str:
        if not self.google_api_key:
            return "Error: GOOGLE_API_KEY not configured."

        llm_text_model = ChatGoogleGenerativeAI(model=FEEDBACK_MODEL, google_api_key=self.google_api_key, convert_system_message_to_human=True)

        try:
            backend_code = read_file_content(backend_code_path)
            frontend_code = read_file_content(frontend_code_path)
        except FileNotFoundError as e:
            return str(e) # Return file not found error to the caller
        except Exception as e:
            return f"Error reading input files: {e}"


        prompt = CODE_QUALITY_PROMPT_TEMPLATE.format(backend_code=backend_code, frontend_code=frontend_code)

        text_evaluation_result = "Failed to get text evaluation."
        try:
            response = llm_text_model.invoke([HumanMessage(content=prompt)])
            text_evaluation_result = response.content
        except Exception as e:
            return f"Error during LLM invocation for code quality text: {e}"

        parsed_output = parse_code_quality_output(text_evaluation_result)

        fe_image_prompt_text = "N/A"
        be_image_prompt_text = "N/A"

        if parsed_output["frontend_score"] is not None:
            fe_image_prompt_text = generate_image_prompt_from_feedback(
                "Frontend Code Quality", parsed_output["frontend_score"], parsed_output["frontend_rationale"], llm_text_model
            )

        if parsed_output["backend_score"] is not None:
            be_image_prompt_text = generate_image_prompt_from_feedback(
                "Backend Code Quality", parsed_output["backend_score"], parsed_output["backend_rationale"], llm_text_model
            )

        # Return the raw JSON string and the image prompts
        return (f"{text_evaluation_result}\n\n"
                f"--- Illustrative Image Prompts Generated (Code Quality) ---\n"
                f"Frontend Code Quality Image Prompt: {fe_image_prompt_text}\n"
                f"Backend Code Quality Image Prompt: {be_image_prompt_text}\n\n")


class AestheticsInput(BaseModel):
    frontend_code_path: str = Field(description="Path to frontend code file for context.")
    screenshot_path: str = Field(description="Path to frontend screenshot image.")

class AestheticsTool(BaseTool):
    name: str = "FrontendAestheticsEvaluator"
    description: str = "Evaluates frontend aesthetics from code and screenshot, and generates an illustrative image. Input: paths to files."
    args_schema: Type[AestheticsInput] = AestheticsInput
    google_api_key: str

    def _run(self, frontend_code_path: str, screenshot_path: str) -> str:
        if not self.google_api_key:
            return "Error: GOOGLE_API_KEY not configured."

        # Use the globally defined FEEDBACK_MODEL that should support vision
        llm_vision_model = ChatGoogleGenerativeAI(model=FEEDBACK_MODEL, google_api_key=self.google_api_key, convert_system_message_to_human=True)
        # Text model for image prompt generation if needed (though generate_image_prompt_from_feedback takes one)
        llm_text_model = ChatGoogleGenerativeAI(model=FEEDBACK_MODEL, google_api_key=self.google_api_key, convert_system_message_to_human=True)

        try:
            frontend_code = read_file_content(frontend_code_path)
        except FileNotFoundError as e:
            return str(e)
        except Exception as e:
            return f"Error reading frontend code file: {e}"


        image_data_url, error = encode_image_to_base64(screenshot_path)
        if error:
            return error # Error message from encode_image_to_base64

        prompt_text = FRONTEND_AESTHETICS_PROMPT_TEMPLATE.format(frontend_code=frontend_code)
        messages = [HumanMessage(content=[ {"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": image_data_url}} ])] # Corrected image_url format

        text_evaluation_result = "Failed to get text evaluation for aesthetics."
        try:
            response = llm_vision_model.invoke(messages)
            text_evaluation_result = response.content
        except Exception as e:
            return f"Error during LLM invocation for aesthetics text: {e}"

        parsed_output = parse_aesthetics_output(text_evaluation_result)
        aesthetic_image_prompt_text = "N/A"

        if parsed_output["score"] is not None:
            aesthetic_image_prompt_text = generate_image_prompt_from_feedback(
                "Frontend Aesthetics & UX", parsed_output["score"], parsed_output["rationale"], llm_text_model
            )

        # Return the raw JSON string and the image prompt
        return (f"{text_evaluation_result}\n\n"
                f"--- Illustrative Image Prompt Generated (Aesthetics) ---\n"
                f"Aesthetics Image Prompt: {aesthetic_image_prompt_text}\n\n")

# --- Main script execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate code quality and frontend aesthetics.")
    parser.add_argument("--frontend-code", default="frontend.txt", help="Path to the frontend code file (e.g., frontend.txt)")
    parser.add_argument("--backend-code", default="backend.txt", help="Path to the backend code file (e.g., backend.txt)")
    parser.add_argument("--screenshot", default="frontend.png", help="Path to the frontend screenshot (e.g., frontend.png)")
    parser.add_argument("--output-file", default="feedback.txt", help="Path to write the evaluation output (e.g., feedback.txt)")
    args = parser.parse_args()

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        exit(1)

    # Check if input files exist before proceeding
    for file_path in [args.frontend_code, args.backend_code, args.screenshot]:
        if not os.path.exists(file_path):
            print(f"Error: Input file not found at {file_path}")
            exit(1)

    print("\n--- Initializing Tools ---")
    code_quality_tool = CodeQualityTool(google_api_key=google_api_key)
    aesthetics_tool = AestheticsTool(google_api_key=google_api_key)

    all_feedback_parts = []

    print("\n--- Code Quality Evaluation ---")
    quality_result = code_quality_tool.run({
        "backend_code_path": args.backend_code,
        "frontend_code_path": args.frontend_code
    })
    print(quality_result) # Print to console for progress
    all_feedback_parts.append("--- Code Quality Evaluation Result ---")
    all_feedback_parts.append(quality_result)


    print("\n--- Frontend Aesthetics Evaluation ---")
    # Screenshot path existence is already checked above
    aesthetics_result = aesthetics_tool.run({
        "frontend_code_path": args.frontend_code,
        "screenshot_path": args.screenshot
    })
    print(aesthetics_result) # Print to console for progress
    all_feedback_parts.append("--- Frontend Aesthetics Evaluation Result ---")
    all_feedback_parts.append(aesthetics_result)

    # Write all feedback to the output file
    try:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(all_feedback_parts))
        print(f"\n--- Evaluation results successfully written to {args.output_file} ---")
    except Exception as e:
        print(f"Error writing results to output file {args.output_file}: {e}")

    print("\n--- Evaluation Script Finished ---")