# Project Context: Information Accessibility Checker

## Project Overview
This is a Python-based web application built using **Streamlit**. Its primary purpose is to serve as an "Information Accessibility Checker" (경평원 정보접근성 검사기), analyzing uploaded images to ensure they meet Web Content Accessibility Guidelines (KWCAG). 

The core engine relies on the **Google Generative AI** API, specifically utilizing the `gemini-3.1-pro-preview` model. It performs rigorous image analysis tasks including:
- **Full OCR (Optical Character Recognition):** Extracting all text from an image without truncation.
- **Contrast Violation Detection:** Exhaustively scanning the image for elements with poor color contrast.
- **QR Code Detection:** Identifying QR codes and providing guidance that they present a barrier to visually impaired users, emphasizing the need for textual URL alternatives.

### Main Technologies
- **Python**
- **Streamlit** (UI and Web Server)
- **Google Generative AI SDK** (`google-generativeai`)
- **Pillow** (Image Processing)

## Building and Running

To set up and run the project locally, follow these steps:

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Secrets:**
   The application requires a valid Google API Key to function. It uses Streamlit's secrets management.
   Create a directory named `.streamlit` in the root of the project and add a `secrets.toml` file:
   ```toml
   # .streamlit/secrets.toml
   GOOGLE_API_KEY = "your_google_api_key_here"
   ```

3. **Run the Application:**
   ```bash
   streamlit run app.py
   ```

## Development Conventions

- **Language:** The application UI, system prompts, and expected outputs are in **Korean**. Future developments, prompt tuning, and UI modifications should maintain this localization.
- **Streamlit Patterns:** The app uses a centered layout (`layout="centered"`). UI updates should follow standard Streamlit functional paradigms.
- **AI Model Configuration:** 
  - **Safety Settings:** The app intentionally sets all safety thresholds to `BLOCK_NONE` to prevent the model from stopping text extraction prematurely. This should be preserved for the OCR functionality to work reliably.
  - **Generation Config:** `temperature` is set to `0.0` for analytical consistency, and `max_output_tokens` is maximized (`8192`) to accommodate lengthy OCR extractions.
- **System Prompt Design:** The system prompt is heavily engineered for "Rigorous Analytical Mode," explicitly forbidding the model from stopping early during OCR or contrast violation checks. Changes to the prompt (`SYSTEM_PROMPT`) must ensure these strict compliance rules remain intact.
