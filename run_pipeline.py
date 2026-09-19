import json
from pathlib import Path

from agents.llm_client import GeminiClient
from agents.pipeline import ResearchPipeline


INPUT = Path("phase1/results/baseline/comparison_output.json")
OUTPUT = Path("phase1/output/final_pipeline_output.json")


def main():
    with INPUT.open("r", encoding="utf-8") as f:
        comparison_input = json.load(f)

    client = GeminiClient()
    pipeline = ResearchPipeline(client)

    result = pipeline.run(comparison_input)

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Pipeline completed.")
    print(f"Final revision number: {result['revision_number']}")
    print(f"Critic decision: {result['critic']['decision']}")
    print(f"Final status: {result['outcome']['final_status']}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
