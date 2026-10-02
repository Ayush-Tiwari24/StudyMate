"""
StudyMate RAG — Evaluation Module

Utilities for running RAGAS evaluation on a test dataset.
"""

from app.core.logger import logger


def evaluate_rag(dataset_path: str = "evaluation/dataset.json") -> dict:
    """
    Run RAGAS evaluation on a Q&A test dataset.
    This is a placeholder — to be implemented when test data is ready.

    Expected dataset format (dataset.json):
    [
        {
            "question": "What is normalization?",
            "ground_truth": "Normalization is the process of...",
            "document": "DBMS_Unit3.pdf"
        },
        ...
    ]
    """
    logger.info(f"Running evaluation on: {dataset_path}")


    return {
        "status": "not_implemented",
        "message": "Add evaluation/dataset.json with Q&A pairs to run evaluation.",
    }
