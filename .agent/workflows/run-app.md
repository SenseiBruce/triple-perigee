---
description: How to run the SonicScript application
---

## Prerequisites
- Python 3.8+
- Node.js 16+

## Running the Application

1. **Start the Backend**
   - In a new terminal, navigate to the root directory.
   - Run the FastAPI server:
   ```bash
   python3 main.py
   ```
   The backend will be available at `http://localhost:8000`.

// turbo
2. **Start the Frontend**
   - In another terminal, navigate to the `frontend` directory:
   ```bash
   cd frontend && npm run dev
   ```
   The frontend will be available at `http://localhost:5173`.

## Usage
1. Open the frontend URL in your browser.
2. Enter your voice-over script in the text area.
3. Select a voice from the settings sidebar.
4. Click "Generate Audio" to create your voice-over.
5. Preview and download the generated MP3.
