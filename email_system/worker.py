from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient, ContentSettings
from azure.storage.queue import QueueClient

from .pipeline import run_pipeline


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip()


def _parse_message(content: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            return json.loads(decoded)
        except (ValueError, json.JSONDecodeError):
            return None


def _extract_blob_name(event: Dict[str, Any], input_container: str) -> Optional[str]:
    if "data" in event and isinstance(event["data"], dict):
        url = event["data"].get("url", "")
        if url:
            marker = f"/{input_container}/"
            idx = url.find(marker)
            if idx >= 0:
                return url[idx + len(marker) :].lstrip("/")
    subject = event.get("subject", "")
    marker = f"/containers/{input_container}/blobs/"
    idx = subject.find(marker)
    if idx >= 0:
        return subject[idx + len(marker) :].lstrip("/")
    return None


def _download_blob_text(blob_service: BlobServiceClient, container: str, blob_name: str) -> str:
    blob = blob_service.get_blob_client(container=container, blob=blob_name)
    data = blob.download_blob().readall()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _upload_output(
    blob_service: BlobServiceClient, container: str, blob_name: str, payload: Dict[str, Any]
) -> None:
    blob = blob_service.get_blob_client(container=container, blob=blob_name)
    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    blob.upload_blob(
        body,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )


def _process_message(
    blob_service: BlobServiceClient,
    input_container: str,
    output_container: str,
    message_content: str,
) -> Optional[str]:
    parsed = _parse_message(message_content)
    if parsed is None:
        return None
    events = parsed if isinstance(parsed, list) else [parsed]
    blob_name = None
    for event in events:
        if isinstance(event, dict):
            blob_name = _extract_blob_name(event, input_container)
            if blob_name:
                break
    if not blob_name:
        return None

    content = _download_blob_text(blob_service, input_container, blob_name)
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        payload = run_pipeline(tmp.name)

    output_name = f"{os.path.splitext(blob_name)[0]}.classified.json"
    _upload_output(blob_service, output_container, output_name, payload)
    return output_name


def main() -> None:
    account_name = _env("STORAGE_ACCOUNT_NAME")
    input_container = _env("INPUT_CONTAINER", "input-email")
    output_container = _env("OUTPUT_CONTAINER", "output-email")
    queue_name = _env("PROCESSING_QUEUE", "processing-queue")
    endpoint = _env("AZURE_OPENAI_ENDPOINT")
    deployment = _env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
    api_key = _env("AZURE_OPENAI_API_KEY")

    if not account_name:
        raise RuntimeError("STORAGE_ACCOUNT_NAME is required.")
    if endpoint:
        print(f"OpenAI endpoint: {endpoint}")
    if deployment:
        print(f"OpenAI embeddings deployment: {deployment}")
    if api_key:
        print(f"OpenAI key length: {len(api_key)}")
    else:
        print("OpenAI key not set.")

    credential = DefaultAzureCredential()
    queue_client = QueueClient(
        account_url=f"https://{account_name}.queue.core.windows.net",
        queue_name=queue_name,
        credential=credential,
    )
    blob_service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential,
    )

    while True:
        messages = queue_client.receive_messages(messages_per_page=1, visibility_timeout=60)
        found = False
        for msg in messages:
            found = True
            try:
                output_name = _process_message(
                    blob_service, input_container, output_container, msg.content
                )
                queue_client.delete_message(msg)
                if output_name:
                    print(f"Processed -> {output_name}")
                else:
                    print("Processed message with no blob.")
            except Exception as exc:
                print(f"Worker error: {exc}")
        if not found:
            time.sleep(2)


if __name__ == "__main__":
    main()
