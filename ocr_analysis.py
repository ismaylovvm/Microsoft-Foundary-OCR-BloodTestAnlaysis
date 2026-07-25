

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
import os
from dotenv import load_dotenv


load_dotenv()


endpoint = os.getenv("ocr_endpoint")
key = os.getenv("ocr_key")

# sample document

document_intelligence_client  = DocumentIntelligenceClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

def analyze_table(image):
    with open(image, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            body=f,
            content_type="application/octet-stream"
        )
    result = poller.result()

    return result