"""Single source of truth for inventory columns (used by schemas, import, export)."""
# (name, kind, max_length, export/import label)   kind: str | text | int | date
FIELDS = [
    ("opco", "str", 100, "OPCO"),
    ("domain", "str", 100, "Domain"),
    ("asset_type", "str", 100, "Asset Type"),
    ("hostname", "str", 255, "Hostname"),
    ("status", "str", 50, "Status"),
    ("ip_address", "str", 45, "IP Address"),
    ("backup_status", "str", 50, "Backup Status"),
    ("ilo_ip", "str", 45, "ILO IP"),
    ("serial_number", "str", 100, "Serial Number"),
    ("application", "text", None, "Application"),
    ("application_owner", "text", None, "Application Owner"),
    ("environment", "str", 20, "Environment"),
    ("bia_class", "str", 50, "Class (BIA)"),
    ("physical_virtual", "str", 20, "Physical / Virtual"),
    ("base_machine", "text", None, "Base Machine"),
    ("base_machine_ip", "text", None, "Base Machine IP"),
    ("virtualization_platform", "str", 100, "Virtualization Platform"),
    ("operating_system", "str", 150, "Operating System"),
    ("memory_gb", "int", None, "Memory (GB)"),
    ("fqdn", "text", None, "FQDN"),
    ("processor_count", "int", None, "Processor Count"),
    ("processor_name", "text", None, "Processor Name"),
    ("mac_address", "text", None, "MAC Address"),
    ("product_name", "text", None, "Product Name"),
    ("hardware_vendor", "str", 100, "Hardware Vendor"),
    ("support_type", "str", 30, "Support Type"),
    ("server_role", "text", None, "Server Role"),
    ("location", "text", None, "Location"),
    ("ito_non_ito", "str", 20, "ITO / Non-ITO"),
    ("end_of_life", "date", None, "End of Life Date"),
    ("end_of_support", "date", None, "End of Support Date"),
    ("oracle_support", "str", 50, "Oracle Support"),
    ("db_version", "str", 50, "Database Version"),
    ("remarks", "text", None, "Remarks"),
]
FIELD_NAMES = [f[0] for f in FIELDS]
KIND = {f[0]: f[1] for f in FIELDS}
MAXLEN = {f[0]: f[2] for f in FIELDS}
LABELS = {f[0]: f[3] for f in FIELDS}
UNIQUE_FIELDS = ("hostname", "ip_address", "serial_number")
SEARCH_FIELDS = ("opco", "domain", "hostname", "ip_address", "serial_number", "application",
                 "application_owner", "operating_system", "environment", "physical_virtual",
                 "backup_status", "product_name", "location", "db_version")
OPTION_FIELDS = ("opco", "domain", "asset_type", "status", "backup_status", "environment",
                 "bia_class", "physical_virtual", "virtualization_platform", "operating_system",
                 "hardware_vendor", "support_type", "ito_non_ito", "oracle_support", "db_version",
                 "location", "application_owner")
