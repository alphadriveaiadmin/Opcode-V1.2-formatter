import json
import textwrap

import requests
import streamlit as st

st.set_page_config(page_title="Service JSON → Markdown Formatter", layout="wide")
st.title("Transportation options, Accepted Payment Methods and Amenities, Services and After Market services Formatter")

st.markdown(
    "Enter the campaign ID and click **Generate Markdown** to retrieve and format "
    "the dealership configuration."
)

campaign_col, _ = st.columns([1, 3])
with campaign_col:
    campaign_id = st.text_input(
        "Campaign ID",
        max_chars=4,
        placeholder="1234",
        help="Enter the 4-digit campaign ID for the webhook.",
    )

raw_json = ""

def format_transportation_name(name: str) -> str:
    """
    Convert uppercase transport name (e.g. 'NIGHT DROP') to 'Night Drop'.
    Keep words like 'service' lowercased if desired.
    """
    if not isinstance(name, str):
        return ""
    # Normalize spaces
    name = " ".join(name.split())
    # Title-case everything, then fix desired special casing
    pretty = name.title()
    # Example: 'Mobile Service' -> 'Mobile service' (to match user's example)
    pretty = pretty.replace("Service", "service")
    return pretty

def build_transportation_section(config_obj: dict) -> str:
    lines = []
    lines.append("### Transportation Options\n")
    lines.append(
        "The transportation options the customer can choose from when booking or "
        "rescheduling an appointment (depending on the services they want to schedule).\n"
    )

    transports = config_obj.get("transportations", [])
    for t in transports:
        name_raw = t.get("transportation", "")
        name = format_transportation_name(name_raw)
        schedule = t.get("schedule_by_agent", "").strip().upper()
        schedule_str = "Yes" if schedule == "YES" else "No"

        qual = (t.get("qualifications_and_params") or "").strip()

        lines.append(f"#### {name}\n")
        lines.append(f"Scheduled by agent: {schedule_str}\n")
        lines.append("Notes:",)

        if qual:
            # Normalize whitespace but keep the raw content (no '>' or '**')
            normalized = textwrap.dedent(qual).strip()
            lines.append("")
            lines.append(normalized)
        else:
            lines.append(" No additional requirements.")

        lines.append("\n---\n")

    return "\n".join(lines).rstrip() + "\n"

def build_payments_and_amenities_section(config_obj: dict) -> str:
    sdi_list = config_obj.get("service_department_information", [])
    payments = []
    amenities = []

    if sdi_list:
        sdi = sdi_list[0]
        payments = sdi.get("methods_accepted_payments", []) or []
        amenities = sdi.get("waiting_lounge_amenities", []) or []

    payments_str = ", ".join(payments) if payments else "Not specified"
    amenities_str = ", ".join(amenities) if amenities else "Not specified"

    lines = []
    lines.append("### Accepted Payment Methods and Amenities\n")
    lines.append("This business accepts the following payment methods:")
    lines.append(payments_str + ".\n")
    lines.append("The waiting lounge offers these amenities:")
    lines.append(amenities_str + ".\n")

    return "\n".join(lines).rstrip() + "\n"

def build_services_section(config_obj: dict) -> str:
    services = config_obj.get("service_mappings", []) or []

    lines = []
    lines.append("# Services\n")
    lines.append(
        "Below are all of the services offered by the car dealership. This section also "
        "includes important information such as the services opCodes, valid "
        "transportation options, and other notes to keep in mind when booking an "
        "appointment with these services.\n"
    )
    lines.append(
        "If the price of a service is 0, inform the customer that an advisor will "
        "provide an estimated price upon arrival to the appointment.\n"
    )
    lines.append("The listed pricing does not include tax or shop supply fees.\n")
    lines.append("---\n")

    for svc in services:
        name = svc.get("service", "")
        opcode = svc.get("opcode", "")
        shop = svc.get("shop", "")
        walk_in = svc.get("walk_in_appointment", "")
        start_price = str(svc.get("starting_price", "0.00"))
        min_wait = svc.get("minimum_wait_time", 0)
        params = (svc.get("params") or "").strip()

        # Collect transportation names from this service
        svc_transports = svc.get("transportations", []) or []
        transport_names = []
        for t in svc_transports:
            t_name = (t.get("transportation") or "").strip().upper()
            if t_name and t_name not in transport_names:
                transport_names.append(t_name)
        transports_str = ", ".join(transport_names) if transport_names else "None"

        lines.append(f"## {name}\n")
        lines.append(f"Opcode: {opcode}")
        lines.append(f"Shop: {shop}")
        lines.append(f"Walk-in appointment: {walk_in}")
        lines.append(f"Starting price: {start_price}")

        try:
            min_wait_val = int(min_wait)
            lines.append(f"Minimum wait time: {min_wait_val} minutes")
        except (ValueError, TypeError):
            lines.append(f"Minimum wait time: {min_wait}")

        if params:
            normalized_params = textwrap.dedent(params).strip()
            lines.append(f"Params: {normalized_params}")
        else:
            lines.append("Params: None specified.")

        lines.append(f"\nAllowed Transportation Options: {transports_str}\n")
        lines.append("---\n")

    return "\n".join(lines).rstrip() + "\n"

def build_aftermarket_section(config_obj: dict) -> str:
    items = config_obj.get("aftermarket_and_sublet_services", []) or []

    lines = []
    lines.append("### After-Market & Sublet Services\n")

    for item in items:
        service = item.get("service", "")
        performed = item.get("performed_by_dealer", "")
        scheduled = item.get("scheduled_by_dga", "")
        process = (item.get("process_to_follow") or "").strip()
        opcode = item.get("opcode")
        opcode_str = opcode if opcode else "N/A"

        lines.append(f"\n## {service}\n")
        lines.append(f"Performed by dealer: {performed}")
        lines.append(f"Scheduled by DGA: {scheduled}")
        lines.append(f"Process to follow: {process}")
        lines.append(f"Opcode: {opcode_str}\n")

    return "\n".join(lines).rstrip() + "\n"

def build_full_markdown(raw: str) -> str:
    data = json.loads(raw)

    # Top-level may be an array of dealership objects
    if isinstance(data, dict):
        dealership_list = [data]
    elif isinstance(data, list):
        dealership_list = data
    else:
        raise ValueError("Top-level JSON must be an object or an array of objects.")

    all_outputs = []

    for idx, obj in enumerate(dealership_list, start=1):
        # Optional: label per-dealer if multiple
        if len(dealership_list) > 1:
            all_outputs.append(f"# Dealership {idx}\n")

        all_outputs.append(build_transportation_section(obj))
        all_outputs.append(build_payments_and_amenities_section(obj))
        all_outputs.append(build_services_section(obj))
        all_outputs.append(build_aftermarket_section(obj))

    return "\n".join(all_outputs).rstrip() + "\n"

generated_markdown = ""
error_message = ""

if st.button("Generate Markdown"):
    if not campaign_id.strip():
        error_message = "Please enter a 4-digit campaign ID before generating."
    elif not campaign_id.isdigit() or len(campaign_id) != 4:
        error_message = "Campaign ID must be exactly 4 digits."
    else:
        try:
            response = requests.post(
                "https://apps.dgaauto.com/virtualAgentData/webhook",
                params={"campaign_id": campaign_id},
                timeout=15,
            )
            response.raise_for_status()
            if response.headers.get("content-type", "").lower().startswith("application/json"):
                raw_json = json.dumps(response.json())
            else:
                raw_json = response.text

            generated_markdown = build_full_markdown(raw_json)
        except Exception as e:
            error_message = f"Error while retrieving or generating markdown: {e}"

if error_message:
    st.error(error_message)

if generated_markdown:
    st.subheader("Generated Markdown")
    st.code(generated_markdown, language="markdown")

    st.download_button(
        label="Download as .md file",
        data=generated_markdown.encode("utf-8"),
        file_name="services_output.md",
        mime="text/markdown",
    )
