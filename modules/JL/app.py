# app.py
# Streamlit app: convert Perfect Love inventory files into Shopify CSV.
# Run: streamlit run app.py

from __future__ import annotations

import csv
import html
import io
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any
from zipfile import ZipFile
from xml.etree import ElementTree as ET

try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

# =========================================================
# Constants
# =========================================================
SHOPIFY_COLUMNS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option1 Linked To",
    "Option2 Name",
    "Option2 Value",
    "Option2 Linked To",
    "Option3 Name",
    "Option3 Value",
    "Option3 Linked To",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare At Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Unit Price Total Measure",
    "Unit Price Total Measure Unit",
    "Unit Price Base Measure",
    "Unit Price Base Measure Unit",
    "Variant Barcode",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Gift Card",
    "SEO Title",
    "SEO Description",
    "Style (product.metafields.custom.style)",
    "Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)",
    "Related products (product.metafields.shopify--discovery--product_recommendation.related_products)",
    "Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)",
    "Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)",
    "Variant Image",
    "Variant Weight Unit",
    "Variant Tax Code",
    "Cost per item",
    "Status",
]

PERFECT_LOVE_REQUIRED_COLUMNS = {
    "Style",
    "Parent-ID",
    "Description",
    "Main-Category",
    "Sub-Category",
    "Mark-Up Price",
}

PERFECT_LOVE_COLUMN_ALIASES = {
    "Style": ["Style", "Stock Number", "Master Stock Number"],
    "Parent-ID": ["Parent-ID", "Master Stock Number", "Stock Number"],
    "Description": ["Description"],
    "Main-Category": ["Main-Category", "Jewelry Sub Type 2", "Jewelry Sub Type"],
    "Sub-Category": ["Sub-Category", "Jewelry Style", "Jewelry Sub Type 1"],
    "Mark-Up Price": ["Mark-Up Price", "Total Sales Price", "Sales Price"],
    "Image-1": ["Image-1", "Image Url 1", "Image URL 1"],
    "Image-2": ["Image-2", "Image Url 2", "Image URL 2"],
    "Image-3": ["Image-3", "Image Url 3", "Image URL 3"],
    "Image-4": ["Image-4", "Image Url 4", "Image URL 4"],
}

IMAGE_COLUMNS = ["Image-1", "Image-2", "Image-3", "Image-4"]
STYLE_FACET_COLUMNS = ["style_category-2", "Style.1", "Style2", "Style3", "Unnamed: 27"]
TAG_MARKER_COLUMNS = {
    "Tag 1 Best Sellers": "Best Seller",
    "Tag 2 - Pearl": "Pearl Collection",
    "Tag 3 - Muse": "Muse Collection",
}
DETAIL_LABEL_OVERRIDES_DEFAULT = {
    "Metal Type": "Metal",
    "Sub-Category": "Jewelry Type",
    "Main-Category": "Category",
    "Total-Diamond Weight (Gram)": "Total Diamond Weight",
    "Total-ColorStone Weight": "Total Color Stone Weight",
    "Total-ColorStone Count": "Total Color Stone Count",
    "Total-ColorStone Type": "Total Color Stone Type",
    "Metal Weight (Gram)": "Metal Weight (g)",
    "Sheet Names": "Sheet Names",
}
DETAIL_FIELD_ORDER = [
    "Metal Type",
    "Sub-Category",
    "Main-Category",
    "Total-Diamond Weight (Gram)",
    "Total-Diamond Count",
    "Diamond Shape",
    "Diamond Color",
    "Diamond Clarity",
    "Total-ColorStone Weight",
    "Total-ColorStone Count",
    "Total-ColorStone Type",
    "ColorStone Shape",
    "Metal Weight (Gram)",
    "Sheet Names",
    "style_category-2",
    "Style.1",
    "Style2",
    "Style3",
    "Unnamed: 27",
]
DEFAULT_DETAIL_FIELDS = [
    "Metal Type",
    "Sub-Category",
    "Total-Diamond Weight (Gram)",
    "Diamond Shape",
    "Diamond Color",
    "Diamond Clarity",
]
SHOPIFY_OUTPUT_HINT_COLUMNS = {"Handle", "Title", "Variant SKU", "Image Src", "Status"}
PLURAL_CATEGORY_TAGS = {
    "Ring": "Rings",
    "Bracelet": "Bracelets",
    "Pendant": "Pendants",
    "Necklace": "Necklaces",
    "Charm": "Charms",
    "Earring": "Earrings",
    "Bangle": "Bangles",
}
SUBCATEGORY_FIXES = {
    "Fashoin Earrings": "Fashion Earrings",
}
ALLOWED_MULTI_VALUE_COLUMNS = {"Sheet_Name", *IMAGE_COLUMNS}


# =========================================================
# Models
# =========================================================
@dataclass
class SourceTable:
    headers: list[str]
    rows: list[dict[str, str]]
    file_type: str
    sheet_name: str = ""
    workbook_sheets: list[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    severity: str
    style: str
    column: str
    message: str


@dataclass
class ProductRecord:
    style: str
    merged: dict[str, str]
    source_rows: list[dict[str, str]]
    sheet_names: list[str]
    marker_tags: list[str]
    images: list[str]
    handle: str = ""


# =========================================================
# Generic helpers
# =========================================================
def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def is_blank(value: Any) -> bool:
    return normalize_text(value) == ""


def ordered_unique(values: list[str]) -> list[str]:
    out = []
    seen = set()
    for value in values:
        text = normalize_text(value)
        key = text.lower()
        if not text or key in seen:
            continue
        out.append(text)
        seen.add(key)
    return out


def slugify(text: str) -> str:
    cleaned = normalize_text(text).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


def split_lines(value: str) -> list[str]:
    parts = []
    for part in normalize_text(value).splitlines():
        cleaned = normalize_text(part)
        if cleaned:
            parts.append(cleaned)
    return parts


def parse_number(value: Any) -> float | int | None:
    text = normalize_text(value).replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return round(number, 4)


def first_non_blank(*values: Any) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def first_number(*values: Any) -> float | int | str:
    for value in values:
        number = parse_number(value)
        if number is not None:
            return number
    return ""


def is_truthy_marker(value: Any) -> bool:
    return normalize_text(value).lower() in {"x", "yes", "true", "1"}


def csv_bytes_from_rows(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return buffer.getvalue().encode("utf-8")


def add_issue(issues: list[ValidationIssue], severity: str, style: str, column: str, message: str) -> None:
    issues.append(ValidationIssue(severity=severity, style=style, column=column, message=message))


# =========================================================
# File readers
# =========================================================
def dedupe_headers(headers: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    out = []
    for raw in headers:
        base = normalize_text(raw) or "Unnamed"
        suffix = counts[base]
        out.append(base if suffix == 0 else f"{base}.{suffix}")
        counts[base] += 1
    return out


def read_csv_table(file_bytes: bytes) -> SourceTable:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    raw_headers = reader.fieldnames or []
    headers = dedupe_headers(raw_headers)
    rows = []
    for raw_row in reader:
        row = {}
        for idx, header in enumerate(headers):
            source_key = raw_headers[idx] if idx < len(raw_headers) else header
            row[header] = normalize_text(raw_row.get(source_key, ""))
        if any(value for value in row.values()):
            rows.append(row)
    return SourceTable(headers=headers, rows=rows, file_type="csv")


def column_ref_to_index(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - 64)
    return value - 1


def read_xlsx_table(file_bytes: bytes) -> SourceTable:
    main_ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    doc_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    with ZipFile(io.BytesIO(file_bytes)) as workbook_zip:
        workbook_xml = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_xml.findall(rel_ns)}

        shared_strings = []
        if "xl/sharedStrings.xml" in workbook_zip.namelist():
            shared_xml = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
            for item in shared_xml.findall("main:si", main_ns):
                text = "".join(
                    node.text or ""
                    for node in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                )
                shared_strings.append(text)

        sheet_nodes = workbook_xml.findall("main:sheets/main:sheet", main_ns)
        workbook_sheets = [node.attrib["name"] for node in sheet_nodes]
        first_sheet = sheet_nodes[0]
        rel_target = rel_map[first_sheet.attrib[doc_rel]]
        if rel_target.startswith("/"):
            sheet_path = rel_target.lstrip("/")
        else:
            sheet_path = str(PurePosixPath("xl") / rel_target)

        sheet_xml = ET.fromstring(workbook_zip.read(sheet_path))
        row_nodes = sheet_xml.findall("main:sheetData/main:row", main_ns)

        parsed_rows = []
        max_col_index = 0
        for row_node in row_nodes:
            cell_map = {}
            for cell in row_node.findall("main:c", main_ns):
                col_index = column_ref_to_index(cell.attrib["r"])
                max_col_index = max(max_col_index, col_index)
                value_node = cell.find("main:v", main_ns)
                inline_node = cell.find("main:is", main_ns)
                cell_type = cell.attrib.get("t")

                value = ""
                if cell_type == "s" and value_node is not None:
                    string_index = int(value_node.text)
                    value = shared_strings[string_index] if string_index < len(shared_strings) else ""
                elif cell_type == "inlineStr" and inline_node is not None:
                    value = "".join(
                        node.text or ""
                        for node in inline_node.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    )
                elif value_node is not None:
                    value = value_node.text or ""

                cell_map[col_index] = normalize_text(value)
            parsed_rows.append([cell_map.get(index, "") for index in range(max_col_index + 1)])

    if not parsed_rows:
        return SourceTable(headers=[], rows=[], file_type="xlsx", sheet_name=first_sheet.attrib["name"])

    headers = dedupe_headers(parsed_rows[0])
    rows = []
    for values in parsed_rows[1:]:
        row = {headers[index]: normalize_text(values[index]) if index < len(values) else "" for index in range(len(headers))}
        if any(value for value in row.values()):
            rows.append(row)

    return SourceTable(
        headers=headers,
        rows=rows,
        file_type="xlsx",
        sheet_name=first_sheet.attrib["name"],
        workbook_sheets=workbook_sheets,
    )


def read_source_table(uploaded_file) -> SourceTable:
    file_name = normalize_text(uploaded_file.name).lower()
    file_bytes = uploaded_file.getvalue()
    if file_name.endswith(".xlsx"):
        return read_xlsx_table(file_bytes)
    if file_name.endswith(".csv"):
        return read_csv_table(file_bytes)
    raise ValueError("Upload a .xlsx or .csv source file.")


# =========================================================
# Schema detection and normalization
# =========================================================
def detect_schema(headers: list[str]) -> str:
    header_set = set(headers)

    if SHOPIFY_OUTPUT_HINT_COLUMNS.issubset(header_set):
        return "shopify_output"

    matched_required = 0
    for canonical, aliases in PERFECT_LOVE_COLUMN_ALIASES.items():
        if canonical not in PERFECT_LOVE_REQUIRED_COLUMNS:
            continue
        if any(alias in header_set for alias in aliases):
            matched_required += 1

    if matched_required == len(PERFECT_LOVE_REQUIRED_COLUMNS):
        return "perfect_love"

    return "unknown"


def pick_first_present(row: dict[str, str], candidates: list[str]) -> str:
    for name in candidates:
        if name in row:
            value = normalize_text(row.get(name))
            if value != "":
                return value
    for name in candidates:
        if name in row:
            return normalize_text(row.get(name))
    return ""


def canonicalize_source_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {key: normalize_text(value) for key, value in row.items()}

    for canonical, aliases in PERFECT_LOVE_COLUMN_ALIASES.items():
        if canonical not in normalized or is_blank(normalized.get(canonical)):
            mapped = pick_first_present(normalized, aliases)
            if mapped != "":
                normalized[canonical] = mapped
            elif canonical not in normalized:
                normalized[canonical] = ""

    return normalized


def normalize_subcategory(value: str) -> str:
    text = normalize_text(value)
    compact = re.sub(r"\s+", " ", text)
    return SUBCATEGORY_FIXES.get(compact, compact)


def normalize_source_row(row: dict[str, str]) -> dict[str, str]:
    normalized = canonicalize_source_row(row)
    normalized["Sub-Category"] = normalize_subcategory(normalized.get("Sub-Category", ""))
    normalized["Main-Category"] = re.sub(r"\s+", " ", normalized.get("Main-Category", ""))
    return normalized


def normalize_source_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [normalize_source_row(row) for row in rows]


# =========================================================
# Product model helpers
# =========================================================
def is_valid_image(url: Any) -> bool:
    value = normalize_text(url)
    if value.lower() in {"0", "image not available", "n/a", "na"}:
        return False
    return value.lower().startswith(("http://", "https://"))


def collect_images(rows: list[dict[str, str]]) -> list[str]:
    images = []
    seen = set()
    for row in rows:
        for column in IMAGE_COLUMNS:
            url = normalize_text(row.get(column))
            if not is_valid_image(url):
                continue
            key = url.lower()
            if key in seen:
                continue
            images.append(url)
            seen.add(key)
    return images


def merge_group_rows(style: str, rows: list[dict[str, str]], headers: list[str], issues: list[ValidationIssue]) -> ProductRecord:
    merged = {}
    for column in headers:
        values = ordered_unique([row.get(column, "") for row in rows])
        if column in ALLOWED_MULTI_VALUE_COLUMNS:
            merged[column] = values[0] if values else ""
            continue
        if len(values) > 1:
            sample_values = " | ".join(values[:3])
            add_issue(
                issues,
                "warning",
                style,
                column,
                f"Conflicting values were found. Using the first non-blank value: {sample_values}",
            )
        merged[column] = values[0] if values else ""

    for canonical in PERFECT_LOVE_COLUMN_ALIASES:
        if canonical not in merged:
            merged[canonical] = first_non_blank(*(row.get(canonical, "") for row in rows))

    sheet_names = ordered_unique([row.get("Sheet_Name", "") for row in rows])
    marker_tags = [
        tag
        for column, tag in TAG_MARKER_COLUMNS.items()
        if any(is_truthy_marker(row.get(column)) for row in rows)
    ]
    images = collect_images(rows)

    if len(ordered_unique([row.get("Parent-ID", "") for row in rows])) > 1:
        add_issue(
            issues,
            "warning",
            style,
            "Parent-ID",
            "The same Style appeared under multiple Parent-ID values.",
        )

    return ProductRecord(
        style=style,
        merged=merged,
        source_rows=rows,
        sheet_names=sheet_names,
        marker_tags=marker_tags,
        images=images,
    )


def assign_unique_handles(products: list[ProductRecord], issues: list[ValidationIssue]) -> None:
    seen: Counter[str] = Counter()
    for product in products:
        base = slugify(product.style) or "product"
        seen[base] += 1
        if seen[base] == 1:
            product.handle = base
            continue
        product.handle = f"{base}-{seen[base]}"
        add_issue(
            issues,
            "warning",
            product.style,
            "Handle",
            f"Slug collision detected. Assigned unique handle '{product.handle}'.",
        )


def aggregate_products(rows: list[dict[str, str]], headers: list[str]) -> tuple[list[ProductRecord], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for index, row in enumerate(rows, start=2):
        style = normalize_text(row.get("Style"))
        if not style:
            add_issue(
                issues,
                "error",
                "",
                "Style",
                f"Source row {index} is missing Style and was skipped.",
            )
            continue
        grouped[style].append(row)

    products = [
        merge_group_rows(style=style, rows=group_rows, headers=headers, issues=issues)
        for style, group_rows in sorted(grouped.items())
    ]
    assign_unique_handles(products, issues)
    return products, issues


# =========================================================
# Shopify mapping helpers
# =========================================================
def normalize_metal_type(row: dict[str, str]) -> str:
    purity = normalize_text(row.get("Metal-Purity"))
    color = normalize_text(row.get("Metal-Color"))
    if not purity and not color:
        return ""

    purity = re.sub(r"(?i)\b(\d{2})\s*kt\b", r"\1K", purity)
    purity = re.sub(r"(?i)\b(\d{2})\s*k\b", r"\1K", purity)
    purity = re.sub(r"\s+", " ", purity).strip()
    color = re.sub(r"\s+", " ", color).strip()

    if color and purity:
        if "gold" in purity.lower():
            prefix = re.sub(r"(?i)\s*gold\b", "", purity).strip()
            return f"{prefix} {color} Gold".strip()
        return f"{purity} {color}".strip()

    return purity or color


def product_type(row: dict[str, str]) -> str:
    return first_non_blank(row.get("Sub-Category"), row.get("Main-Category"), "Jewelry")


def style_traits(row: dict[str, str]) -> list[str]:
    traits = []
    for column in STYLE_FACET_COLUMNS:
        value = normalize_text(row.get(column))
        if not value:
            continue
        traits.extend(split_lines(value))
    return ordered_unique(traits)


def sheet_name_aliases(sheet_names: list[str]) -> list[str]:
    aliases = []
    for name in sheet_names:
        alias = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        if alias and alias != name:
            aliases.append(alias)
    return ordered_unique(aliases)


def detail_value(product: ProductRecord, field_name: str) -> str:
    row = product.merged
    if field_name == "Metal Type":
        return normalize_metal_type(row)
    if field_name == "Sheet Names":
        return ", ".join(product.sheet_names)
    return normalize_text(row.get(field_name))


def available_detail_fields(products: list[ProductRecord]) -> list[str]:
    available = []
    for field_name in DETAIL_FIELD_ORDER:
        if any(detail_value(product, field_name) for product in products):
            available.append(field_name)
    return available


def build_body_html(product: ProductRecord, selected_fields: list[str], label_overrides: dict[str, str]) -> str:
    row = product.merged
    description = normalize_text(row.get("Description"))
    parts = []
    if description:
        parts.append(f"<p>{html.escape(description)}</p>")

    detail_lines = []
    for field_name in selected_fields:
        value = detail_value(product, field_name)
        if not value:
            continue
        label = label_overrides.get(field_name, field_name)
        detail_lines.append(
            f"<p><strong>{html.escape(label)}</strong> - {html.escape(value)}</p>"
        )

    if detail_lines:
        parts.append("<hr><h3>Details</h3>" + "".join(detail_lines))

    return "".join(parts)


def build_tags(product: ProductRecord, item_location: str) -> str:
    row = product.merged
    tags = []

    tags.extend(product.sheet_names)
    tags.extend(sheet_name_aliases(product.sheet_names))
    tags.extend(product.marker_tags)

    main_category = normalize_text(row.get("Main-Category"))
    sub_category = product_type(row)
    if main_category:
        tags.append(main_category)
        plural = PLURAL_CATEGORY_TAGS.get(main_category)
        if plural:
            tags.append(plural)
    if sub_category:
        tags.append(sub_category)

    collection = normalize_text(row.get("Collection"))
    if collection:
        tags.append(collection)

    for trait in style_traits(row):
        tags.append(trait)

    metal_type = normalize_metal_type(row)
    if metal_type:
        tags.append(f"Metal_{metal_type}")

    diamond_shape = normalize_text(row.get("Diamond Shape"))
    diamond_color = normalize_text(row.get("Diamond Color"))
    diamond_clarity = normalize_text(row.get("Diamond Clarity"))
    if diamond_shape:
        tags.append(f"Diamond Shape_{diamond_shape}")
    if diamond_color:
        tags.append(f"Diamond Color_{diamond_color}")
    if diamond_clarity:
        tags.append(f"Diamond Clarity_{diamond_clarity}")

    if item_location:
        tags.append(f"Item Location_{item_location}")

    return ", ".join(ordered_unique(tags))


def default_variant_option(product: ProductRecord) -> tuple[str, str]:
    metal_type = normalize_metal_type(product.merged)
    if metal_type:
        return "Metal Type", metal_type
    return "Title", "Default Title"


def seo_title(product: ProductRecord) -> str:
    return first_non_blank(product.merged.get("Rule"), product.style)


def seo_description(product: ProductRecord) -> str:
    return first_non_blank(product.merged.get("Description"))


def style_metafield_value(product: ProductRecord) -> str:
    traits = style_traits(product.merged)
    return "\n".join(traits)


def base_shopify_row() -> dict[str, Any]:
    return {column: "" for column in SHOPIFY_COLUMNS}


def product_rows_to_shopify(
    products: list[ProductRecord],
    vendor_name: str,
    item_location: str,
    selected_detail_fields: list[str],
    label_overrides: dict[str, str],
    include_products_without_images: bool,
) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    rows_out: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []

    for product in products:
        row = product.merged
        price = first_number(row.get("Mark-Up Price"))
        cost = first_number(
            row.get("Cost Price + 10% Tariff"),
            row.get("Cost Price"),
            row.get("Cost Price.1"),
        )
        grams = first_number(row.get("Metal Weight (Gram)"))
        main_row = base_shopify_row()
        option_name, option_value = default_variant_option(product)
        primary_image = product.images[0] if product.images else ""
        image_alt = first_non_blank(product.style, row.get("Description"))

        if price == "":
            add_issue(
                issues,
                "warning",
                product.style,
                "Mark-Up Price",
                "The product is missing Mark-Up Price. Variant Price will be blank.",
            )

        if not product.images:
            message = "No valid image URL was found."
            if include_products_without_images:
                add_issue(
                    issues,
                    "warning",
                    product.style,
                    "Images",
                    f"{message} The product will export without images.",
                )
            else:
                add_issue(
                    issues,
                    "warning",
                    product.style,
                    "Images",
                    f"{message} The product was skipped because 'Include products without valid images' is turned off.",
                )
                continue

        if not normalize_text(row.get("Description")):
            add_issue(
                issues,
                "warning",
                product.style,
                "Description",
                "The product is missing Description.",
            )

        main_row["Handle"] = product.handle
        main_row["Title"] = product.style
        main_row["Body (HTML)"] = build_body_html(product, selected_detail_fields, label_overrides)
        main_row["Vendor"] = vendor_name
        main_row["Type"] = product_type(row)
        main_row["Tags"] = build_tags(product, item_location=item_location)
        main_row["Published"] = True
        main_row["Option1 Name"] = option_name
        main_row["Option1 Value"] = option_value
        main_row["Variant SKU"] = product.style
        main_row["Variant Grams"] = grams if grams != "" else 0
        main_row["Variant Inventory Tracker"] = "shopify"
        main_row["Variant Inventory Qty"] = 1
        main_row["Variant Inventory Policy"] = "deny"
        main_row["Variant Fulfillment Service"] = "manual"
        main_row["Variant Price"] = price
        main_row["Variant Requires Shipping"] = True
        main_row["Variant Taxable"] = True
        main_row["Gift Card"] = False
        main_row["SEO Title"] = seo_title(product)
        main_row["SEO Description"] = seo_description(product)
        main_row["Style (product.metafields.custom.style)"] = style_metafield_value(product)
        main_row["Variant Image"] = primary_image
        main_row["Variant Weight Unit"] = "g"
        main_row["Cost per item"] = cost
        main_row["Status"] = "active"

        if primary_image:
            main_row["Image Src"] = primary_image
            main_row["Image Position"] = 1
            main_row["Image Alt Text"] = image_alt

        rows_out.append(main_row)

        for position, image_url in enumerate(product.images[1:], start=2):
            image_row = base_shopify_row()
            image_row["Handle"] = product.handle
            image_row["Image Src"] = image_url
            image_row["Image Position"] = position
            image_row["Image Alt Text"] = image_alt
            rows_out.append(image_row)

    return rows_out, issues


# =========================================================
# Validation summaries
# =========================================================
def build_summary_rows(products: list[ProductRecord], source_rows: list[dict[str, str]], issues: list[ValidationIssue]) -> dict[str, int]:
    duplicate_styles = sum(1 for product in products if len(product.source_rows) > 1)
    missing_images = sum(1 for product in products if not product.images)
    missing_prices = sum(
        1 for product in products if first_number(product.merged.get("Mark-Up Price")) == ""
    )
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    errors = sum(1 for issue in issues if issue.severity == "error")
    return {
        "source_rows": len(source_rows),
        "products": len(products),
        "duplicate_styles": duplicate_styles,
        "missing_images": missing_images,
        "missing_prices": missing_prices,
        "warnings": warnings,
        "errors": errors,
    }


def issues_to_rows(issues: list[ValidationIssue]) -> list[dict[str, str]]:
    return [
        {
            "Severity": issue.severity,
            "Style": issue.style,
            "Column": issue.column,
            "Message": issue.message,
        }
        for issue in issues
    ]


def product_preview_rows(products: list[ProductRecord], limit: int = 25) -> list[dict[str, Any]]:
    preview = []
    for product in products[:limit]:
        preview.append(
            {
                "Style": product.style,
                "Parent-ID": product.merged.get("Parent-ID", ""),
                "Sheet Names": ", ".join(product.sheet_names),
                "Type": product_type(product.merged),
                "Price": first_number(product.merged.get("Mark-Up Price")),
                "Cost": first_number(
                    product.merged.get("Cost Price + 10% Tariff"),
                    product.merged.get("Cost Price"),
                    product.merged.get("Cost Price.1"),
                ),
                "Images": len(product.images),
                "Handle": product.handle,
            }
        )
    return preview


# =========================================================
# Streamlit app
# =========================================================
def main():
    if st is None:
        raise RuntimeError("Streamlit is required to run the UI. Install streamlit and run `streamlit run app.py`.")

    st.set_page_config(page_title="Perfect Love Shopify Converter", layout="wide")
    st.title("Perfect Love Shopify Converter")
    st.caption("Upload the source inventory workbook or CSV, review the merged product preview, then download a clean Shopify CSV.")

    with st.sidebar:
        st.header("Output Settings")
        vendor_name = st.text_input("Vendor Name", value="Perfect Love Inventory")
        item_location = st.text_input("Item Location", value="United States")
        include_products_without_images = st.checkbox(
            "Include products without valid images",
            value=True,
        )

    uploaded_file = st.file_uploader("Upload Perfect Love source file", type=["xlsx", "csv"])
    if uploaded_file is None:
        st.info("Upload a .xlsx or .csv source file to begin.")
        st.stop()

    try:
        source_table = read_source_table(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the source file: {exc}")
        st.stop()

    schema = detect_schema(source_table.headers)
    if schema == "shopify_output":
        st.error("This file already looks like Shopify output. Upload the source inventory workbook or source-format CSV instead.")
        st.stop()
    if schema != "perfect_love":
        st.error(
            "The uploaded file does not match the expected Perfect Love source schema. "
            "Accepted columns include either the original names or compatible aliases such as "
            "Stock Number, Master Stock Number, Jewelry Sub Type 2, Jewelry Style, Total Sales Price, and Image Url 1."
        )
        st.stop()

    source_rows = normalize_source_rows(source_table.rows)
    products, merge_issues = aggregate_products(source_rows, source_table.headers)
    summary = build_summary_rows(products, source_rows, merge_issues)

    st.subheader("Source Preview")
    if source_table.file_type == "xlsx":
        st.caption(
            f"Workbook sheet used: `{source_table.sheet_name}`"
            + (
                f" | Workbook sheets: {', '.join(source_table.workbook_sheets)}"
                if source_table.workbook_sheets
                else ""
            )
        )
    st.write(f"Raw rows: {summary['source_rows']:,} | Unique products after merging by Style: {summary['products']:,}")
    st.dataframe(source_rows[:25], use_container_width=True)

    st.subheader("Validation Summary")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Raw Rows", summary["source_rows"])
    c2.metric("Products", summary["products"])
    c3.metric("Merged Duplicates", summary["duplicate_styles"])
    c4.metric("Missing Images", summary["missing_images"])
    c5.metric("Missing Prices", summary["missing_prices"])
    c6.metric("Warnings", summary["warnings"])

    if summary["errors"]:
        st.error(f"{summary['errors']} row-level errors were found. Affected rows were skipped.")

    issue_rows = issues_to_rows(merge_issues)
    if issue_rows:
        with st.expander("Review detected issues"):
            st.dataframe(issue_rows[:200], use_container_width=True)
            st.download_button(
                "Download validation report",
                data=csv_bytes_from_rows(issue_rows, ["Severity", "Style", "Column", "Message"]),
                file_name="perfect_love_validation_report.csv",
                mime="text/csv",
            )

    st.subheader("Merged Product Preview")
    st.dataframe(product_preview_rows(products), use_container_width=True)

    available_fields = available_detail_fields(products)
    default_detail_fields = [field for field in DEFAULT_DETAIL_FIELDS if field in available_fields]

    st.subheader("Body HTML Details")
    selected_detail_fields = st.multiselect(
        "Select fields to show in the Shopify Body HTML details section",
        options=available_fields,
        default=default_detail_fields,
    )

    label_overrides = dict(DETAIL_LABEL_OVERRIDES_DEFAULT)
    with st.expander("Rename Body HTML labels"):
        for field_name in selected_detail_fields:
            default_label = label_overrides.get(field_name, field_name)
            new_label = st.text_input(f"Label for {field_name}", value=default_label, key=f"lbl_{field_name}")
            if normalize_text(new_label):
                label_overrides[field_name] = normalize_text(new_label)

    if not normalize_text(vendor_name):
        st.warning("Enter a Vendor Name in the sidebar before generating the Shopify CSV.")
        st.stop()

    if st.button("Generate Shopify CSV", type="primary"):
        output_rows, conversion_issues = product_rows_to_shopify(
            products=products,
            vendor_name=normalize_text(vendor_name),
            item_location=normalize_text(item_location),
            selected_detail_fields=selected_detail_fields,
            label_overrides=label_overrides,
            include_products_without_images=include_products_without_images,
        )

        all_issue_rows = issues_to_rows(merge_issues + conversion_issues)
        if all_issue_rows:
            st.warning(f"The export completed with {len(all_issue_rows)} warnings or errors. Review the validation report if needed.")

        st.success(f"Generated Shopify CSV with {len(output_rows):,} row(s).")
        st.subheader("Shopify Output Preview")
        st.dataframe(output_rows[:50], use_container_width=True)

        base_name = normalize_text(uploaded_file.name).rsplit(".", 1)[0]
        st.download_button(
            "Download Shopify CSV",
            data=csv_bytes_from_rows(output_rows, SHOPIFY_COLUMNS),
            file_name=f"{base_name}_SHOPIFY.csv",
            mime="text/csv",
        )

        if all_issue_rows:
            st.download_button(
                "Download Full Validation Report",
                data=csv_bytes_from_rows(all_issue_rows, ["Severity", "Style", "Column", "Message"]),
                file_name=f"{base_name}_VALIDATION.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()
