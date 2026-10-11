# 🌸 SakhiSahay — Women's Healthcare Platform

**Your health. Your journey. Your companion.**

SakhiSahay is a multilingual, AI-powered women's healthcare platform designed to make health information more accessible, understandable, and personalized. It combines a Retrieval-Augmented Generation (RAG) health assistant, menstrual and symptom tracking, data-driven health insights, and access to healthcare professionals in one unified experience.

> Built with the goal of combining AI, Data Science, and full-stack development to support more informed women's healthcare decisions.

---

## ✨ Key Features

### 🤖 1. AI Health Assistant
- RAG-based question answering using a curated women's health knowledge base.
- Semantic retrieval using vector embeddings and Qdrant.
- Context-grounded responses generated using Google Gemini.
- Source references to help users explore the underlying information.
- Concise, structured answers designed to reduce unsupported medical claims.
- A safety-first approach: educational support, not medical diagnosis.

### 🌷 2. Period & Symptom Tracker
- Log menstrual periods and daily symptoms.
- Maintain a history of cycle and symptom records.
- Visualize cycle information using a calendar interface.
- Explore symptom frequencies and historical patterns.
- Generate simple, data-driven insights from recorded information.
- Distinguish recorded history from estimated cycle dates.

### 📊 3. Personalized Health Insights
- Analyze longitudinal symptom records.
- Summarize recurring patterns across logged cycles.
- Visualize cycle history and symptom trends.
- Support health awareness without diagnosing medical conditions.

### 🩺 4. Doctor Connect
- Explore healthcare professionals and specialties.
- View doctor profiles and consultation details.
- Support an appointment discovery and booking workflow.

*Feature availability depends on the current implementation. Clearly label prototype or planned features that are not yet fully functional.*

---

## 🧠 How the AI Assistant Works

SakhiSahay uses **Retrieval-Augmented Generation (RAG)** to ground its answers in a curated knowledge base rather than relying solely on a language model's pretrained knowledge.

```text
Curated Medical Documents
          │
          ▼
  Text Extraction & Cleaning
          │
          ▼
       Chunking
          │
          ▼
   Embedding Generation
          │
          ▼
    Qdrant Vector Store
          │
          ▼
       User Question
          │
          ▼
 Semantic Retrieval of Relevant Chunks
          │
          ▼
   Evidence Sufficiency Check
          │
          ▼
     Google Gemini LLM
          │
          ▼
 Concise, Structured Answer
          │
          ▼
    Source References
```

### RAG pipeline highlights

- **Knowledge ingestion:** Prepare trusted medical documents for retrieval.
- **Chunking:** Split documents into manageable passages while preserving relevant context.
- **Embeddings:** Represent document passages and user questions as vectors.
- **Vector search:** Retrieve semantically relevant passages using Qdrant.
- **Grounded generation:** Use Gemini to synthesize and structure information supported by the retrieved passages.
- **Source attribution:** Associate answers with the actual retrieved sources.
- **Insufficient-evidence handling:** Avoid fabricating source-backed answers when the available context is inadequate.

The goal is to use the LLM primarily for language synthesis and presentation while keeping medical knowledge grounded in retrieved evidence.

---

## 🏗️ System Architecture

```text
              ┌─────────────────────┐
              │   React Frontend    │
              │ Dashboard & Modules │
              └──────────┬──────────┘
                         │ REST API
                         ▼
              ┌─────────────────────┐
              │   FastAPI Backend   │
              └──────────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     AI Assistant   Health Tracker   Doctor Connect
          │              │              │
          ▼              ▼              ▼
     RAG Pipeline    Structured DB   Appointment APIs
          │
          ▼
     Qdrant Vector DB
          │
          ▼
      Gemini LLM
```

The exact database and module integrations should reflect the implementation in the repository.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React / existing frontend stack |
| Backend | Python, FastAPI |
| LLM | Google Gemini |
| RAG | Retrieval-Augmented Generation |
| Vector Database | Qdrant |
| Embeddings | Sentence Transformers / configured embedding model |
| Document Processing | PyMuPDF and text-processing utilities |
| Data Science | Python, Pandas, NumPy |
| API Communication | REST APIs |
| Version Control | Git and GitHub |

*Replace alternatives with the exact technologies currently used in the codebase.*

---

## 📂 Project Structure

An illustrative structure for the project:

```text
SakhiSahay/
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── Backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── rag/
│   │   ├── services/
│   │   └── schemas/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── data/
│   └── raw/
│
├── docs/
└── README.md
```

Your actual repository may differ. Keep this section synchronized with the real folder structure.

---

## 🚀 Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.11 or the version required by your backend.
- Node.js and npm, if using React.
- A Qdrant instance or supported local persistent storage configuration.
- A Google Gemini API key if the selected model requires one.
- Git.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/SakhiSahay.git
cd SakhiSahay
```

Replace `YOUR_USERNAME` with your GitHub username and adjust the repository name if necessary.

### 2. Configure the backend

```bash
cd Backend
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file from the example:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Configure the required environment variables according to the project's settings, including the LLM API key and Qdrant configuration.

**Never commit `.env` or API keys to GitHub.**

### 3. Prepare the knowledge base

Place approved medical documents in the ingestion directory configured by the backend.

Run the repository's ingestion command to extract text, create chunks, generate embeddings, and index them in Qdrant.

For example, if the project uses this entry point:

```bash
python -m scripts.ingest_documents
```

Use the actual command implemented in your repository. Confirm that ingestion completes successfully and that the indexed collection persists across restarts.

### 4. Start the backend

From the backend directory, run the FastAPI application using the configured entry point.

For example:

```bash
uvicorn app.main:app --reload
```

If the backend entry point differs, use the corresponding module path.

When running locally, the API documentation is commonly available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health` (if implemented)

### 5. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Configure the frontend API base URL to point to the running backend, using the environment-variable convention already present in the project.

Open the local development URL printed by the frontend command.

---

## 🧪 Testing the RAG Assistant

Evaluate the assistant using questions whose answers are represented in your knowledge base.

Example test questions:

- What is PMS?
- What is the difference between a period and a menstrual cycle?
- What information should I record in a symptom tracker?
- What does the knowledge base say about common period discomfort?
- Ask a question that is not covered by the indexed documents.

Check whether the assistant:

1. Retrieves relevant passages.
2. Answers the specific question directly.
3. Avoids adding unsupported medical facts.
4. Returns genuine source references.
5. Acknowledges insufficient evidence.
6. Preserves appropriate safety guidance.

Run the automated tests available in the repository:

```bash
pytest
```

Use the actual test command configured by the project if different.

---

## 🔐 Privacy & Responsible AI

SakhiSahay is intended to support health education and awareness, not replace qualified healthcare professionals.

- AI-generated information should not be treated as a diagnosis.
- Answers should be grounded in trusted sources where possible.
- Insufficient evidence should be acknowledged rather than concealed.
- Sensitive health data should be protected through appropriate authentication and access controls.
- User-specific health records should remain separate from the general medical knowledge base.
- Medical safety guidance should be reviewed and tested.
- Users should seek qualified professional care for individualized medical concerns.

Do not use demo records or fictional doctor profiles as evidence of real patient activity or verified clinical services.

---

## 🗺️ Roadmap

- [x] Frontend design and core application layout
- [x] Initial RAG architecture
- [ ] Robust document ingestion and incremental indexing
- [ ] Improved semantic retrieval and evidence filtering
- [ ] Grounded answers with validated source references
- [ ] Complete period and symptom tracking integration
- [ ] Personalized statistical health insights
- [ ] Multilingual support for Hindi and Hinglish
- [ ] Doctor discovery and appointment workflow
- [ ] Comprehensive safety and evaluation testing
- [ ] Production deployment and monitoring

Update the checkboxes to reflect the actual status of each feature.

---

## 🎯 Project Objectives

SakhiSahay explores how modern AI and data-driven application development can be combined to:

- Improve access to understandable women's health information.
- Apply RAG to domain-specific question answering.
- Retrieve and synthesize information from a curated knowledge base.
- Analyze longitudinal symptom data.
- Build an integrated full-stack healthcare application.
- Apply privacy-conscious and responsible AI design principles.

## 🤝 Contributing

Contributions, suggestions, and feedback are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Run relevant tests.
5. Submit a pull request with a clear description of the changes.

## ⚠️ Disclaimer

SakhiSahay is an educational and academic software project. It is not a substitute for professional medical advice, diagnosis, or treatment. Do not rely on the prototype for emergency or clinical decision-making.

## 👩‍💻 Author

**Atharv Sharma**

B.Tech — Computer Science & Engineering, Data Science

University of Petroleum and Energy Studies (UPES)

GitHub: [YOUR_GITHUB_USERNAME](https://github.com/YOUR_GITHUB_USERNAME)

---

⭐ If you find this project interesting, consider starring the repository.
