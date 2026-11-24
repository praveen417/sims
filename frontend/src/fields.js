// Mirrors backend/app/fields.py
export const FIELDS = [
  { name: "opco", label: "OPCO", kind: "str" },
  { name: "domain", label: "Domain", kind: "str" },
  { name: "asset_type", label: "Asset Type", kind: "str" },
  { name: "hostname", label: "Hostname", kind: "str" },
  { name: "status", label: "Status", kind: "str" },
  { name: "ip_address", label: "IP Address", kind: "str" },
  { name: "backup_status", label: "Backup Status", kind: "str" },
  { name: "ilo_ip", label: "ILO IP", kind: "str" },
  { name: "serial_number", label: "Serial Number", kind: "str" },
  { name: "application", label: "Application", kind: "text" },
  { name: "application_owner", label: "Application Owner", kind: "text" },
  { name: "environment", label: "Environment", kind: "str", options: ["Prod", "DR", "UAT", "Dev", "Test"] },
  { name: "bia_class", label: "Class (BIA)", kind: "str" },
  { name: "physical_virtual", label: "Physical / Virtual", kind: "str", options: ["Physical", "Virtual"] },
  { name: "base_machine", label: "Base Machine", kind: "text" },
  { name: "base_machine_ip", label: "Base Machine IP", kind: "text" },
  { name: "virtualization_platform", label: "Virtualization Platform", kind: "str" },
  { name: "operating_system", label: "Operating System", kind: "str" },
  { name: "memory_gb", label: "Memory (GB)", kind: "int" },
  { name: "fqdn", label: "FQDN", kind: "text" },
  { name: "processor_count", label: "Processor Count", kind: "int" },
  { name: "processor_name", label: "Processor Name", kind: "text" },
  { name: "mac_address", label: "MAC Address", kind: "text" },
  { name: "product_name", label: "Product Name", kind: "text" },
  { name: "hardware_vendor", label: "Hardware Vendor", kind: "str" },
  { name: "support_type", label: "Support Type", kind: "str" },
  { name: "server_role", label: "Server Role", kind: "text" },
  { name: "location", label: "Location", kind: "text" },
  { name: "ito_non_ito", label: "ITO / Non-ITO", kind: "str" },
  { name: "end_of_life", label: "End of Life Date", kind: "date" },
  { name: "end_of_support", label: "End of Support Date", kind: "date" },
  { name: "oracle_support", label: "Oracle Support", kind: "str" },
  { name: "db_version", label: "Database Version", kind: "str" },
  { name: "remarks", label: "Remarks", kind: "text" },
];
export const KIND = Object.fromEntries(FIELDS.map((f) => [f.name, f.kind]));
export const UNIQUE = ["hostname", "ip_address", "serial_number"];
export const ROLES = ["admin", "manager", "developer", "requester", "readonly"];

// text from a form/grid -> value for the API ("" clears the field)
export function coerce(name, v) {
  if (v === undefined || v === null || String(v).trim() === "") return null;
  if (KIND[name] === "int") {
    const n = Number(v);
    if (Number.isNaN(n)) throw new Error(`${name} must be a number`);
    return Math.trunc(n);
  }
  return String(v).trim();
}
