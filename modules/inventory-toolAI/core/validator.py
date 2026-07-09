def build_qa_report(source_df, normalized_df, output_df, config):
    warnings = []

    source_rows = len(source_df) if source_df is not None else 0
    normalized_rows = len(normalized_df) if normalized_df is not None else 0
    output_rows = len(output_df) if output_df is not None else 0

    duplicate_skus = 0
    if output_df is not None and "Stock Number" in output_df.columns:
        duplicate_skus = int(output_df["Stock Number"].duplicated().sum())
        if duplicate_skus:
            warnings.append(f"Duplicate Stock Number values found: {duplicate_skus}")

    missing_master_stock = 0
    for col in ["Master Stock Number", "Master stock", "Master Stock"]:
        if normalized_df is not None and col in normalized_df.columns:
            missing_master_stock = int((normalized_df[col].astype(str).str.strip() == "").sum())
            break

    if missing_master_stock:
        warnings.append(f"Missing master stock values: {missing_master_stock}")

    low_confidence = [
        x for x in config.get("mapping", [])
        if float(x.get("confidence", 0)) < 0.8
    ]

    if low_confidence:
        warnings.append(f"Low confidence mappings: {len(low_confidence)}")

    return {
        "source_rows": source_rows,
        "normalized_rows": normalized_rows,
        "output_rows": output_rows,
        "duplicate_skus": duplicate_skus,
        "missing_master_stock": missing_master_stock,
        "warnings": warnings,
    }
