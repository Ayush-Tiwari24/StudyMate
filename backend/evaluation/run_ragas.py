"""
StudyMate RAG — RAGAS Evaluation Runner

Runs evaluation metrics on the Q&A test set.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_evaluation(dataset_path: str = "evaluation/dataset.json"):
    """Run RAGAS evaluation. Placeholder for now."""
    with open(dataset_path) as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} Q&A pairs from {dataset_path}")
    print("TODO: Implement RAGAS evaluation with actual RAG pipeline")
    print("Expected metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "evaluation/dataset.json"
    run_evaluation(path)
