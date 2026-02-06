from __future__ import annotations

from pathlib import Path

import typer

from .io import save_output
from .pipeline import run_pipeline

app = typer.Typer(add_completion=False, help="Automatic email categorization pipeline.")


@app.command()
def run(
    input_path: str = typer.Argument(..., help="Path to JSON file or directory of JSON files."),
    output_path: str = typer.Argument(..., help="Path to write the output JSON."),
) -> None:
    payload = run_pipeline(input_path)
    save_output(output_path, payload)
    typer.echo(f"Wrote results to {Path(output_path).resolve()}")

