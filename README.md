# Blood Test OCR & AI Interpretation

*[Türkçe için tıklayın](README.tr.md)*

## About the Project

This project is a web application that automatically reads and
interprets a blood test report image. The user uploads a blood test
image; the system extracts the test results using OCR, determines
whether each value is within the normal range, and produces a
plain-language explanation through a local AI model.

> **Note:** This application does not provide a medical diagnosis. All
> interpretations it generates are for informational purposes only;
> always consult a doctor for an accurate evaluation.

## Technologies Used

- **Python 3**
- **Streamlit** — web interface
- **Azure AI Document Intelligence** — extracting table data from the image (OCR)
- **Foundry Local (Phi-4-mini)** — local language model that interprets the results

## Project Structure

```
analiz/
├── app.py               # Streamlit interface (upload, table, chat)
├── llm_analysis.py       # LLM interpretation and chat flow
├── ocr_analysis.py       # OCR processing via Azure Document Intelligence
├── data_process.py       # Parses OCR output and determines low/high/normal status
├── .env                  # Azure connection details (ocr_endpoint, ocr_key)
└── README.md
```

## How It Works

1. The user uploads a blood test image from the **OCR Results** tab.
2. When **Analyze** is clicked, the image is sent to Azure Document
   Intelligence, which extracts the test results (test name, value,
   unit, reference range) from the table.
3. Each test result is classified as **Low / High / Normal** by
   comparing it against its reference range, and shown in a table on
   the right.
4. The user switches to the **AI Interpretation & Q&A** tab and clicks
   **Generate Interpretation**; the results are sent to a local
   language model (Phi-4-mini), which explains what each test means,
   possible causes, and recommendations.
5. After this initial interpretation, the user can freely ask follow-up
   questions about the results (e.g. *"what is hemoglobin?"*).

## Setup

```bash
python -m venv venv
venv\Scripts\activate

python -m pip install streamlit azure-ai-documentintelligence foundry-local-sdk python-dotenv
```

Create a `.env` file in the project folder with your Azure Document
Intelligence credentials:

```
ocr_endpoint=https://<your-resource-name>.cognitiveservices.azure.com/
ocr_key=<your-key>
```

## Usage

```bash
streamlit run app.py
```

Once the app is running:
1. Upload a report image from the **OCR Results** tab, click **Analyze**.
2. Review the extracted test results (with status labels) in the table.
3. Switch to the **AI Interpretation & Q&A** tab and click **Generate
   Interpretation** for the overall assessment.
4. Ask any follow-up questions about the results.

## Status Determination Logic

The status of each test result (`low` / `high` / `normal`) is not left
to the model — it is determined in code:

1. If the report already marks a value with `[H]` / `[L]`, that marker
   is trusted.
2. Otherwise, the value and reference range are converted to numbers
   and compared directly.
3. If the value or range isn't in a standard format, the status is
   marked as `unknown`.

This separation is intentional: status determination always comes from
deterministic code, while interpretation and recommendations come from
the language model — this removes the risk of the model making an
error in numerical comparison.

## Limitations

- Works reliably only with table-formatted reports.
- If the reference range isn't in a standard (`min-max`) format, the
  status may be marked as `unknown`.
- Low image quality can cause OCR to misread some values.
- Results are not stored persistently; the report is reprocessed on
  every session.
