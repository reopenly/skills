---
name: reopenly-embedding-generate-dataset
description: Use the current LLM to create embedding training triplets from document chunks in a CSV, then save anchor, positive, and negative columns to a CSV file.
compatibility: Requires Python 3.9+ and access to the current LLM. Generation may consume many tokens.
---

# Generate an embedding dataset from CSV document chunks

1. Ask for the input CSV path, the column containing document chunks, and the output CSV path if these are not provided. Each non-empty row in the selected column is one document chunk. Do not send the file to an external model or API; use the current LLM.
2. Inspect the CSV header and use the bundled helper to count its bytes, data rows, non-empty chunks, and blank chunks:

   ```sh
   python3 /path/to/reopenly-embedding-generate-dataset/scripts/csv_tools.py inspect \
     --file /path/to/documents.csv --column chunk
   ```

   Before generating anything, tell the user the CSV file size, number of document chunks to process, number of blank rows that will be skipped, and that exactly one anchor question will be generated per non-empty chunk (N questions total). Explain that the current LLM will also generate one negative passage per chunk, so token use depends on chunk and output lengths. Ask the user to explicitly confirm. Do not generate until they approve.

3. After approval, read the CSV using CSV-aware parsing and process every non-empty chunk. Work in manageable batches, maintaining each row's one-based **data-record index** (first data row is 1; the header is not counted). For each chunk, use this instruction:

   > Using only the document chunk below, create exactly one concise, natural question whose answer is directly supported by the chunk. Return the question as `anchor`. Return the original chunk verbatim as `positive`; do not summarize, correct, or rewrite it. Create one concise `negative` passage that is clearly not an answer to the anchor. Prefer an unrelated or contrasting passage over invented factual claims. Do not use information outside the chunk to write the anchor. Return only a JSON object with string fields `anchor` and `negative`.

   Keep a JSONL sidecar of generated results, one object per non-empty input record, in this form (record indices are one-based data-record indices):

   ```json
   {"data_row": 1, "anchor": "...", "negative": "..."}
   ```

   The positive field is intentionally not regenerated: the finalizer copies the exact original chunk from the source CSV. Never silently drop a non-empty input chunk. If generation fails for a row, stop and report the row; do not produce a partial output as if complete.

4. Build the output CSV with the helper, using the JSONL sidecar and chosen destination:

   ```sh
   python3 /path/to/reopenly-embedding-generate-dataset/scripts/csv_tools.py finalize \
     --file /path/to/documents.csv --column chunk \
     --generated /path/to/generated.jsonl --output /path/to/embedding-pairs.csv
   ```

   The output header is exactly `anchor,positive,negative`. The helper verifies that every non-empty input record has exactly one generated result, preserves each positive chunk verbatim, and refuses to overwrite an existing output unless the user explicitly approves overwrite and `--overwrite` is used. Report the output path and number of generated rows.

Do not upload or train on the resulting CSV unless separately asked. This skill only generates a local dataset.
