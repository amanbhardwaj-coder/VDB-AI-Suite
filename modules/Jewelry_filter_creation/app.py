import streamlit as st
from shared.constants import VDB_LOGO_URL
import json
import pandas as pd
import io
import re

# ==========================================
# 1. HARDCODED COMMON FILTERS
# ==========================================
COMMON_FILTERS = [
    {
        "name": "Metal", "type": "checkbox-list", "label": "searchForm.jewelry.metal.text",
        "order": 3, "payload_name": ["metals"], "has_separator": True, "is_collapsible": True,
        "selection_type": "multiple", "collection_dependencies": ["Essentials", "Bridals", "Haute Couture", "Fashion Collections", "All-Collections", "Men"],
        "options": [
            {"icon": {"data": "two_tone", "type": "img"}, "name": "Two Tone", "type": "text-list", "label": "searchForm.jewelry.metal.mixMetal.text", "order": 1, "search_payload": ["MIX Metal"]},
            {"icon": {"data": "platinum", "type": "img"}, "name": "Platinum", "type": "text-list", "label": "searchForm.jewelry.metal.platinum.text", "order": 2, "search_payload": ["Platinum"]},
            {"icon": {"data": "silver", "type": "img"}, "name": "Silver", "type": "text-list", "label": "searchForm.jewelry.metal.silver.text", "order": 3, "search_payload": ["Silver"]},
            {"icon": {"data": "white_gold", "type": "img"}, "name": "White Gold", "type": "text-list", "label": "searchForm.jewelry.metal.whiteGold.text", "order": 4, "search_payload": ["White Gold"]},
            {"icon": {"data": "yellow_gold", "type": "img"}, "name": "Yellow Gold", "type": "text-list", "label": "searchForm.jewelry.metal.yellowGold.text", "order": 5, "search_payload": ["Yellow Gold"]},
            {"icon": {"data": "rose_gold", "type": "img"}, "name": "Rose Gold", "type": "text-list", "label": "searchForm.jewelry.metal.roseGold.text", "order": 6, "search_payload": ["Rose Gold"]},
            {"icon": {"data": "", "type": ""}, "name": "Other", "type": "text-list", "label": "searchForm.jewelry.metal.other.text", "order": 9, "search_payload": ["other"]}
        ]
    },
    {
        "name": "Total Price", "type": "list", "label": "searchForm.jewelry.totalPrice.text",
        "order": 4, "max_row": 1, "price_modes": [1, 2], "display_title": True,
        "sub_filters": [{
            "max": 1000, "min": 26, "name": "Total Price", "type": "range", "label": "searchForm.jewelry.totalPrice.text",
            "order": 11, "maxLabel": "searchForm.jewelry.totalPrice.maxLabel.text", "minLabel": "searchForm.jewelry.totalPrice.minLabel.text",
            "price_modes": [0, 1, 2], "payload_name": ["price_total_from", "price_total_to"], "selection_type": "range",
            "collection_dependencies": ["Essentials", "Bridals", "Haute Couture", "Fashion Collections", "All-Collections", "Men"]
        }]
    },
    {
        "max": 100, "min": 0, "name": "Centre Stone Weight", "type": "range-list", "label": "searchForm.jewelry.carat.text",
        "order": 5, "columns": 3, "max_row": 3, "payload_name": ["size_from", "size_to"], "selection_type": "range",
        "maxLabel": "searchForm.jewelry.carat.maxLabel.text", "minLabel": "searchForm.jewelry.carat.minLabel.text",
        "collection_dependencies": ["Essentials", "Bridals", "Haute Couture", "Fashion Collections", "All-Collections", "Men"],
        "options": [
            {"name": "0.30-0.39", "label": "0.30-0.39", "order": 1, "price_modes": [0, 1, 2], "search_payload": [0.3, 0.39]},
            {"name": "0.40-0.49", "label": "0.40-0.49", "order": 2, "price_modes": [0, 1, 2], "search_payload": [0.4, 0.49]},
            {"name": "0.50-0.69", "label": "0.50-0.69", "order": 3, "price_modes": [0, 1, 2], "search_payload": [0.5, 0.69]},
            {"name": "1.00-1.49", "label": "1.00-1.49", "order": 6, "price_modes": [0, 1, 2], "search_payload": [1, 1.49]}
        ]
    },
    {
        "api": "jewelries/locations_search", "name": "Location", "type": "dropdown",
        "label": "Search by Location", "order": 6, "icon_name": "global-search",
        "input_label": "searchForm.jewelry.location.dropdown.inputLabel.text",
        "price_modes": [], "payload_name": ["vendor_locations"], "api_query_key": "q", "selection_type": "multiple"
    },
    {
        "api": "jewelries/all_jewelry_brands", "name": "Brand", "type": "dropdown",
        "label": "Search by Brand", "order": 7, "icon_name": "brand",
        "input_label": "searchForm.jewelry.brand.dropdown.inputLabel.text",
        "price_modes": [], "payload_name": ["brands"], "api_query_key": "q", "selection_type": "multiple"
    }
]

def clean_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def clean_deps(dep_string):
    if pd.isna(dep_string):
        return []
    return [clean_value(d) for d in str(dep_string).split(",") if clean_value(d)]


def deps_group_key(dep_string):
    return "||".join(clean_deps(dep_string))


def safe_id(*parts):
    chunks = []
    for part in parts:
        text = clean_value(part)
        if not text:
            continue
        text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
        if text:
            chunks.append(text)
    return "__".join(chunks)


def make_filter_name(filter_label, payload_name, parent_key=None, parent_value=None, collection_key=None):
    return safe_id(filter_label, parent_value, collection_key)


def create_option(row, icon_type="img"):
    option_name = clean_value(row["option_name"])
    search_payload = clean_value(row["search_payload"])
    option_internal_name = option_name if option_name == search_payload else safe_id(option_name, search_payload)

    return {
        "icon": {"data": "", "type": icon_type},
        "name": option_internal_name,
        "type": "text-list",
        "label": option_name,
        "price_modes": [0, 1, 2],
        "search_payload": [search_payload]
    }

st.set_page_config(page_title="Jewelry JSON Generator", page_icon=VDB_LOGO_URL)

st.title("Jewelry Filter JSON Generator")
st.markdown("Upload your configured Excel template to instantly generate the frontend JSON configuration.")

uploaded_file = st.file_uploader("Upload your Excel mapping file (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        collections_df = pd.read_excel(uploaded_file, sheet_name="Collections")
        lvl1_df = pd.read_excel(uploaded_file, sheet_name="Level1_Filters")
        lvl2_df = pd.read_excel(uploaded_file, sheet_name="Level2_Filters")
        
        all_col_options = [{"name": "All-Collections", "label": "All Collections", "collection": "All-Collections", "sectionName": "Jewelry", "predefined_payload": {}}]
        all_col_options += [{"name": str(c), "label": str(c), "collection": str(c), "sectionName": "Jewelry", "predefined_payload": {}} for c in collections_df["collection_name"].tolist()]

        collections_dropdown = {
            "name": "Collections", "step": 1, "type": "collection-dropdown",
            "label": "Collection / Category", "order": 0, "platforms": ["web"],
            "options": all_col_options, "payload_name": ["collection"],
            "collection_dependencies": collections_df["collection_name"].tolist() + ["All-Collections"]
        }

        dynamic_blocks = [collections_dropdown]

        if not lvl1_df.empty:
            lvl1_df = lvl1_df.copy()
            lvl1_df["_collection_dependency_key"] = lvl1_df["collection_dependency"].apply(deps_group_key)

            grouped_l1 = lvl1_df.groupby(
                ["filter_label", "payload_name", "_collection_dependency_key"],
                dropna=False,
                sort=False
            )
            for (f_label, p_name, c_deps_key), group in grouped_l1:
                group = group.drop_duplicates(subset=["option_name", "search_payload"], keep="first")
                options = [create_option(row, "img") for _, row in group.iterrows()]
                for idx, opt in enumerate(options, 1): opt["order"] = idx

                block = {
                    "name": make_filter_name(f_label, p_name, collection_key=c_deps_key),
                    "type": "checkbox-list",
                    "label": clean_value(f_label),
                    "order": 1,
                    "columns": 4 if len(options) <= 8 else 3,
                    "max_row": 3,
                    "options": options,
                    "payload_name": [clean_value(p_name)],
                    "has_separator": True,
                    "selection_type": "single",
                    "additional_filters": True,
                    "collection_dependencies": clean_deps(group.iloc[0]["collection_dependency"])
                }
                dynamic_blocks.append(block)

        if not lvl2_df.empty:
            lvl2_df = lvl2_df.copy()
            lvl2_df["_collection_dependency_key"] = lvl2_df["collection_dependency"].apply(deps_group_key)

            grouped_l2 = lvl2_df.groupby(
                ["filter_label", "payload_name", "parent_payload_key", "parent_payload_value", "_collection_dependency_key"],
                dropna=False,
                sort=False
            )
            for (f_label, p_name, parent_key, parent_val, c_deps_key), group in grouped_l2:
                group = group.drop_duplicates(subset=["option_name", "search_payload"], keep="first")
                options = [create_option(row, "font") for _, row in group.iterrows()]
                for idx, opt in enumerate(options, 1): opt["order"] = idx

                block = {
                    "name": make_filter_name(f_label, p_name, parent_key, parent_val, c_deps_key),
                    "type": "text-list",
                    "label": clean_value(f_label),
                    "order": 2,
                    "columns": 2,
                    "max_row": 4,
                    "options": options,
                    "price_modes": [0, 1, 2],
                    "dependencies": [{"key": clean_value(parent_key), "value": clean_value(parent_val)}],
                    "payload_name": [clean_value(p_name)],
                    "has_separator": True,
                    "is_collapsible": True,
                    "selection_type": "multiple",
                    "additional_filters": True,
                    "is_default_collapsed": False,
                    "collection_dependencies": clean_deps(group.iloc[0]["collection_dependency"])
                }
                dynamic_blocks.append(block)

        final_json = {
            "jewelry": [{
                "name": "Jewelry",
                "type": "tabs",
                "label": "searchForm.jewelry.jewelry.text",
                "order": 1,
                "sub_type": None,
                "price_modes": [0, 1, 2],
                "isCollection": True,
                "filters": dynamic_blocks + COMMON_FILTERS
            }]
        }

        json_string = json.dumps(final_json, indent=2, ensure_ascii=False)

        st.success("✅ JSON successfully generated!")
        
        st.download_button(
            label="Download Generated JSON",
            data=json_string,
            file_name="Searchform.generated.json",
            mime="application/json"
        )
        
        with st.expander("Preview JSON"):
            st.json(final_json)

    except Exception as e:
        st.error(f"❌ Error reading Excel file. Make sure your Excel file has the exact sheets: 'Collections', 'Level1_Filters', and 'Level2_Filters'.\n\nDetails: {e}")
