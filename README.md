# Resume Tailor AI

Resume Tailor AI is a local Streamlit application that turns a base resume PDF and a pasted job description into ATS-optimized application materials. It uses a local Ollama model to generate a tailored resume and cover letter, then provides before and after ATS keyword scores, downloadable PDFs, and copyable LaTeX.

## Features

- Upload a PDF resume and extract its text locally.
- Paste a job description and calculate a before-generation ATS match score.
- Generate a truthful, tailored resume with a local Ollama LLM.
- Generate a concise cover letter based on the tailored resume.
- View after-generation ATS score and score improvement.
- Download the tailored resume and cover letter as PDFs.
- Copy complete LaTeX source for both generated documents.
- Review matched, missing, and AI-added keywords.

## Prerequisites

- Python 3.11 or newer.
- Git.
- Ollama installed and running locally.
- A local Ollama model pulled, for example:

```bash
ollama pull llama3.2
```

## Installation

Clone the repository, then create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Optionally copy the environment example:

```bash
cp .env.example .env
```

## How To Run

Start Ollama in the background if it is not already running, then launch Streamlit:

```bash
streamlit run app.py
```

Open the local URL Streamlit prints in your terminal.

## Usage

1. Upload a text-based PDF resume in the sidebar.
2. Paste a job description with at least 500 characters.
3. Enter your name, email, and phone number.
4. Choose `llama3.2` or `qwen2.5:7b`.
5. Click **Generate Tailored Materials**.
6. Review the before and after ATS scores, download PDFs, or reveal the LaTeX code.

The app only uses local processing and the local Ollama API at `http://localhost:11434`.

## Tech Stack

- Streamlit
- LangChain
- Ollama through `langchain-ollama`
- pdfplumber
- scikit-learn
- Jinja2
- WeasyPrint
- ReportLab

## License

MIT
