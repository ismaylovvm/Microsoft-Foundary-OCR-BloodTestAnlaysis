from foundry_local_sdk import Configuration, FoundryLocalManager
from ocr_analysis import analyze_table
from data_process import parse_table

SOURCE_FILE = "example_data/example2.png"
FOUNDRY_APP_NAME = "foundry_local_samples"
MODEL_NAME = "phi-4-mini"

SYSTEM_PROMPT = """
You are an experienced physician explaining blood test results to a patient. 
Your goal is to provide a professional, clear, medically accurate, and very simple interpretation of the laboratory report.

Instructions:

1. Analyze the ENTIRE report before answering.
2. Analyze EVERY test exactly once in the order they appear. Never skip any test.
3. Use the provided "status" field as the correct classification. Do not recalculate.

4. For EACH test, keep your explanation strictly to these 3 simple steps:

   * **What it is:** Provide the [Test Name], [Result], and [Status]. Explain briefly and simply what this test measures in the body.
   * **Causes:** If the result is abnormal (High/Low), explain the most common reasons or causes for this specific result. (If normal, simply state it indicates good health).
   * **Solutions:** If the result is abnormal, provide clear, practical, and safe recommendations (diet, lifestyle, or medical next steps) to fix or manage it. (If normal, skip this part).

5. After explaining every individual test using the 3 steps above, provide a brief **Overall Assessment** summarizing the general health picture and how the abnormal results might be connected.


"""

INITIAL_PROMPT = (
    "Please provide a complete and simple interpretation of my blood test report. "
    "Analyze every test result one by one following the 3 steps (What it is, Causes, Solutions), then provide an overall medical assessment."
    "Give solutions for every test result"
)


def build_context(parsed_result):
    satirlar = []

    for row in parsed_result:
        unit = row.get("unit") or "-"
        ref = row.get("reference_range") or "-"
        status = row.get("status") or "unknown"

        satirlar.append(
            f"- {row['test_name']}: {row['value']} {unit} "
            f"(referans: {ref}, durum: {status})"
        )

    return "patient's blood analysis results :\n" + "\n".join(satirlar)


def analyze_blood_test(image_path: str) -> list[dict]:
    result = analyze_table(image_path)
    return parse_table(result)


def initialize_manager(progress_callback=None):
    config = Configuration(app_name=FOUNDRY_APP_NAME)
    if getattr(FoundryLocalManager, "instance", None) is None:
        try:
            FoundryLocalManager.initialize(config)
        except RuntimeError as exc:
            if "already been initialized" not in str(exc):
                raise
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps(progress_callback=progress_callback)
    return manager


def load_model_and_client(manager, download_progress=None):
    model = manager.catalog.get_model(MODEL_NAME)
    model.download(download_progress or (lambda _progress: None))
    model.load()
    return model, model.get_chat_client()


def build_system_message(parsed_result):
    return {
        "role": "system",
        "content": SYSTEM_PROMPT + "\n\n" + build_context(parsed_result),
    }


def create_initial_messages(parsed_result):
    return [
        build_system_message(parsed_result),
        {"role": "user", "content": INITIAL_PROMPT},
    ]


def build_api_messages(parsed_result, conversation):
    """conversation: list of user/assistant dicts (no system)."""
    messages = [build_system_message(parsed_result)]
    messages.extend(conversation)
    return messages


def stream_chat_response(client, messages):
    for chunk in client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            yield content


def main():
    current_ep = ""

    def ep_progress(ep_name: str, percent: float):
        nonlocal current_ep
        if ep_name != current_ep:
            if current_ep:
                print()
            current_ep = ep_name
        print(f"\r  {ep_name:<30}  {percent:5.1f}%", end="", flush=True)

    manager = initialize_manager(progress_callback=ep_progress)
    if current_ep:
        print()

    print("blood test is being analyzed...")
    parsed_result = analyze_blood_test(SOURCE_FILE)
    print(f"{len(parsed_result)} finded test result.\n")

    model, client = load_model_and_client(
        manager,
        download_progress=lambda progress: print(
            f"\rDownloading model: {progress:.2f}%", end="", flush=True
        ),
    )
    print()
    print("Model loaded and ready.")

    messages = create_initial_messages(parsed_result)

    print("\nAsistan: ", end="", flush=True)
    full_response = ""
    for content in stream_chat_response(client, messages):
        print(content, end="", flush=True)
        full_response += content
    print("\n")
    messages.append({"role": "assistant", "content": full_response})

    print("You can ask questions related with results. write 'quit' to leave... )\n")

    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ("quit", "exit"):
            break

        messages.append({"role": "user", "content": user_input})

        print("Assistan: ", end="", flush=True)
        full_response = ""
        for content in stream_chat_response(client, messages):
            print(content, end="", flush=True)
            full_response += content
        print("\n")

        messages.append({"role": "assistant", "content": full_response})

    model.unload()
    print("Model unloaded. Görüşürüz!")


if __name__ == "__main__":
    main()
