"""/mitre/[assessmentId] — Results, largest screen. Source: inventory/mitre.md §0, §3, §5.
Interaction core (run timeline slider + Play + per-cell tooltip) lifted from
docs/design/hero-views-2026-09-12/gen.py MITRE_BODY/MITRE_SCRIPT and adapted to the
sc-for/VALS format."""
from dc import (T, app_shell, screen, btn, chip, dot_chip, kpi, icon, tabs, panel, sheet, dialog,
                 th, dth, dcell, states, skel, alert, esc)

STEM = "MitreDetail"
PAGE, TITLE, ORDER = "mitre", "MITRE assessment results", 30

# ------------------------------------------------------------------ §0 shared vocab
STATE_LABEL = {"covered": "Covered", "partial": "Partial", "not_covered": "Not covered", "na": "N/A"}
STATE_TIP = {
    "covered": "At least one enabled detection rule maps here with high confidence.",
    "partial": "Only a disabled rule, a lower-confidence AI mapping, or a covered sub-technique reaches this — treat it as half-covered.",
    "not_covered": "No detection rule maps here — this technique is a gap.",
    "na": "Doesn't apply to your environment (or was excluded by you), so it doesn't count toward the coverage percentage.",
}
STATE_PLAIN = {"covered": "A rule detects this", "partial": "Half-covered", "not_covered": "No rule detects this", "na": "Doesn't apply to your environment"}
STATE_TONE = {"covered": "ok", "partial": "med", "not_covered": "crit", "na": "grey"}
THREAT_LABELS = "Financial Services, Scattered Spider, LockBit affiliates, Asia-Pacific, APT41, Lazarus Group, Kimsuky, Mustang Panda"

# ------------------------------------------------------------------ tactic/cell data (compact but real)
def cell(id, name, state, since=9, rule=None, source=None, subs=None):
    return {"id": id, "name": name, "state": state, "since": since, "rule": rule, "source": source, "subs": subs or []}


ENTERPRISE_TACTICS = [
    ("recon", "Reconnaissance", 3, 46, [
        cell("T1595", "Active Scanning", "not_covered"),
        cell("T1592", "Gather Victim Host Information", "not_covered"),
        cell("T1589", "Gather Victim Identity Information", "covered", 2, "Rule 4 · Phishing URL click", "Secure email gateway"),
        cell("T1598", "Phishing for Information", "covered", 5, "Rule 12 · Impossible travel sign-in", "Entra sign-in logs",
             subs=[cell("T1598.003", "Spearphishing Link", "partial", 3, "Rule 4 (email gateway only, no click telemetry)", "Secure email gateway")]),
        cell("T1597", "Search Closed Sources", "na"),
        cell("T1596", "Search Open Technical Databases", "not_covered"),
    ]),
    ("resdev", "Resource Development", 0, 50, [
        cell("T1583", "Acquire Infrastructure", "not_covered"),
        cell("T1586", "Compromise Accounts", "not_covered"),
        cell("T1587", "Develop Capabilities", "not_covered"),
        cell("T1608", "Stage Capabilities", "not_covered"),
        cell("T1584", "Compromise Infrastructure", "not_covered"),
        cell("T1585", "Establish Accounts", "na"),
    ]),
    ("ia", "Initial Access", 7, 22, [
        cell("T1133", "External Remote Services", "not_covered"),
        cell("T1190", "Exploit Public-Facing Application", "covered", 1, "Rule 33 · WAF exploit signature", "WAF logs"),
        cell("T1566", "Phishing", "covered", 1, "Rule 4 · Phishing URL click", "Secure email gateway",
             subs=[cell("T1566.001", "Spearphishing Attachment", "covered", 4, "Rule 4 · Phishing URL click", "Secure email gateway")]),
        cell("T1078", "Valid Accounts", "covered", 0, "Rule 12 · Impossible travel sign-in", "Entra sign-in logs",
             subs=[cell("T1078.004", "Cloud Accounts", "partial", 5, "Rule 141 (Entra risk signal, no MFA context)", "Entra sign-in logs")]),
        cell("T1195", "Supply Chain Compromise", "not_covered"),
        cell("T1091", "Replication Through Removable Media", "not_covered"),
    ]),
    ("exec", "Execution", 15, 64, [
        cell("T1059", "Command and Scripting Interpreter", "covered", 0, "Rule 8 · PowerShell encoded command", "Windows Event Logs (Sysmon)",
             subs=[cell("T1059.001", "PowerShell", "covered", 0, "Rule 8 · PowerShell encoded command", "Windows Event Logs (Sysmon)"),
                   cell("T1059.003", "Windows Command Shell", "not_covered")]),
        cell("T1053", "Scheduled Task/Job", "covered", 1, "Rule 21 · Scheduled task created", "Windows Event Logs"),
        cell("T1047", "Windows Management Instrumentation", "covered", 3, "Rule 77 · WMI remote exec", "Windows Event Logs (Sysmon)"),
        cell("T1204", "User Execution", "not_covered"),
        cell("T1569", "System Services", "covered", 6, "Rule 150 · Service installed", "Windows Event Logs"),
        cell("T1129", "Shared Modules", "na"),
    ]),
    ("persist", "Persistence", 22, 113, [
        cell("T1098", "Account Manipulation", "covered", 2, "Rule 40 · Account manipulation", "Entra audit logs"),
        cell("T1136", "Create Account", "covered", 2, "Rule 41 · Local account created", "Windows Event Logs",
             subs=[cell("T1136.001", "Local Account", "not_covered")]),
        cell("T1543", "Create or Modify System Process", "partial", 4, "Rule 62 (disabled — Windows service only)", "Windows Event Logs (Sysmon)"),
        cell("T1547", "Boot or Logon Autostart Execution", "covered", 3, "Rule 62 · Run key added", "Windows Event Logs (Sysmon)"),
        cell("T1546", "Event Triggered Execution", "not_covered"),
        cell("T1037", "Boot or Logon Initialization Scripts", "not_covered"),
    ]),
    ("privesc", "Privilege Escalation", 19, 96, [
        cell("T1055", "Process Injection", "covered", 1, "Rule 15 · Process injection (EDR)", "EDR (CrowdStrike)"),
        cell("T1068", "Exploitation for Privilege Escalation", "not_covered"),
        cell("T1548", "Abuse Elevation Control Mechanism", "partial", 2, "Rule 90 (AI-mapped, confidence 0.5)", "Windows Event Logs"),
        cell("T1484", "Domain or Tenant Policy Modification", "covered", 4, "Rule 90 · GPO modified", "Windows Event Logs"),
        cell("T1134", "Access Token Manipulation", "not_covered"),
        cell("T1611", "Escape to Host", "na"),
    ]),
    ("de", "Defense Evasion", 14, 148, [
        cell("T1027", "Obfuscated Files or Information", "partial", 2, "Rule 44 (keyword-matched, no entropy check)", "Windows Event Logs (Sysmon)"),
        cell("T1070", "Indicator Removal", "covered", 0, "Rule 2 · Event log cleared", "Windows Event Logs"),
        cell("T1562", "Impair Defenses", "covered", 5, "Rule 132 · Defender disabled", "EDR (Microsoft Defender for Endpoint)"),
        cell("T1036", "Masquerading", "not_covered"),
        cell("T1218", "System Binary Proxy Execution", "covered", 6, "Rule 152 · Signed binary proxy execution", "EDR (CrowdStrike)"),
        cell("T1557", "Adversary-in-the-Middle", "not_covered"),
    ]),
    ("ca", "Credential Access", 16, 67, [
        cell("T1003", "OS Credential Dumping", "covered", 0, "Rule 1 · LSASS access", "EDR (CrowdStrike)"),
        cell("T1110", "Brute Force", "covered", 1, "Rule 9 · Brute force", "Entra sign-in logs"),
        cell("T1552", "Unsecured Credentials", "not_covered",
             subs=[cell("T1552.001", "Credentials In Files", "not_covered")]),
        cell("T1555", "Credentials from Password Stores", "not_covered"),
        cell("T1558", "Steal or Forge Kerberos Tickets", "covered", 4, "Rule 88 · Kerberoasting", "Windows Event Logs"),
        cell("T1621", "Multi-Factor Authentication Request Generation", "covered", 7, "Rule 170 · MFA fatigue", "Identity provider MFA logs"),
    ]),
    ("disc", "Discovery", 12, 49, [
        cell("T1082", "System Information Discovery", "not_covered"),
        cell("T1087", "Account Discovery", "covered", 3, "Rule 40 · Account manipulation", "Entra audit logs"),
        cell("T1018", "Remote System Discovery", "not_covered"),
        cell("T1046", "Network Service Scanning", "not_covered"),
        cell("T1057", "Process Discovery", "na"),
        cell("T1518", "Software Discovery", "not_covered"),
    ]),
    ("lm", "Lateral Movement", 9, 23, [
        cell("T1021", "Remote Services", "covered", 0, "Rule 5 · RDP lateral", "Windows Event Logs"),
        cell("T1080", "Taint Shared Content", "not_covered"),
        cell("T1210", "Exploitation of Remote Services", "not_covered"),
        cell("T1219", "Remote Access Software", "not_covered"),
        cell("T1570", "Lateral Tool Transfer", "not_covered"),
        cell("T1550", "Use Alternate Authentication Material", "covered", 5, "Rule 139 · Pass-the-hash", "Windows Event Logs (Sysmon)"),
    ]),
    ("coll", "Collection", 9, 41, [
        cell("T1560", "Archive Collected Data", "not_covered"),
        cell("T1005", "Data from Local System", "covered", 4, "Rule 21 · Scheduled task created", "Windows Event Logs"),
        cell("T1114", "Email Collection", "not_covered"),
        cell("T1113", "Screen Capture", "na"),
        cell("T1074", "Data Staged", "not_covered"),
        cell("T1119", "Automated Collection", "not_covered"),
    ]),
    ("c2", "Command and Control", 5, 70, [
        cell("T1071", "Application Layer Protocol", "covered", 3, "Rule 44 (keyword-matched, no entropy check)", "Windows Event Logs (Sysmon)"),
        cell("T1573", "Encrypted Channel", "not_covered"),
        cell("T1090", "Proxy", "not_covered"),
        cell("T1105", "Ingress Tool Transfer", "covered", 6, "Rule 152 · Signed binary proxy execution", "EDR (CrowdStrike)"),
        cell("T1102", "Web Service", "na"),
        cell("T1132", "Data Encoding", "not_covered"),
    ]),
    ("exfil", "Exfiltration", 2, 28, [
        cell("T1041", "Exfiltration Over C2 Channel", "covered", 6, "Rule 155 · C2 exfil volume", "Firewall / NetFlow"),
        cell("T1048", "Exfiltration Over Alternative Protocol", "not_covered"),
        cell("T1567", "Exfiltration Over Web Service", "not_covered"),
        cell("T1020", "Automated Exfiltration", "not_covered"),
        cell("T1030", "Data Transfer Size Limits", "not_covered"),
        cell("T1029", "Scheduled Transfer", "na"),
    ]),
    ("impact", "Impact", 4, 47, [
        cell("T1486", "Data Encrypted for Impact", "covered", 2, "Rule 173 · Mass file rename/encrypt pattern", "EDR (CrowdStrike)"),
        cell("T1490", "Inhibit System Recovery", "covered", 5, "Rule 173 · Mass file rename/encrypt pattern", "EDR (CrowdStrike)"),
        cell("T1489", "Service Stop", "not_covered"),
        cell("T1499", "Endpoint Denial of Service", "not_covered"),
        cell("T1485", "Data Destruction", "not_covered"),
        cell("T1491", "Defacement", "na"),
    ]),
]

ICS_TACTICS = [
    ("ics_ia", "Initial Access", 1, 21, [cell("T0817", "Drive-by Compromise", "not_covered"), cell("T0819", "Exploit Public-Facing Application", "covered", 4, "Rule 33 · WAF exploit signature (OT DMZ)", "WAF logs"), cell("T0822", "External Remote Services", "not_covered")]),
    ("ics_ev", "Evasion", 0, 18, [cell("T0849", "Masquerading", "not_covered"), cell("T0851", "Rootkit", "not_covered"), cell("T0872", "Indicator Removal on Host", "na")]),
    ("ics_coll", "Collection", 1, 15, [cell("T0802", "Automated Collection", "not_covered"), cell("T0801", "Monitor Process State", "covered", 7, "Rule 190 · HMI process-state poll anomaly", "OT historian logs"), cell("T0845", "Program Upload", "not_covered")]),
    ("ics_impact", "Impact", 3, 42, [cell("T0813", "Denial of Control", "not_covered"), cell("T0828", "Loss of Productivity and Revenue", "not_covered"), cell("T0831", "Manipulation of Control", "na")]),
]

MOBILE_TACTICS = [
    ("mob_ia", "Initial Access", 0, 24, [cell("T1660", "Phishing", "not_covered"), cell("T1461", "Lock Screen Bypass", "not_covered"), cell("T1456", "Drive-By Compromise", "na")]),
    ("mob_persist", "Persistence", 1, 30, [cell("T1633", "Foreground Persistence", "not_covered"), cell("T1603", "Scheduled Task/Job", "covered", 6, "Rule 205 · MDM scheduled-job anomaly", "MDM (Intune)"), cell("T1624", "Event Triggered Execution", "not_covered")]),
    ("mob_ca", "Credential Access", 0, 26, [cell("T1417", "Input Capture", "not_covered"), cell("T1414", "Clipboard Data", "not_covered"), cell("T1634", "Credentials from Password Store", "na")]),
    ("mob_disc", "Discovery", 1, 45, [cell("T1418", "Software Discovery", "not_covered"), cell("T1420", "File and Directory Discovery", "not_covered"), cell("T1426", "System Information Discovery", "covered", 7, "Rule 210 · MDM device-info exfil check", "MDM (Intune)")]),
]

DOMAINS = [("enterprise", "Enterprise", 125, 697, ENTERPRISE_TACTICS), ("ics", "ICS / OT", 5, 96, ICS_TACTICS), ("mobile", "Mobile", 2, 125, MOBILE_TACTICS)]

RUN_DATES = ["Jun 13, 2026, 09:05 AM", "Jun 27, 2026, 09:14 AM", "Jul 11, 2026, 08:40 AM", "Jul 25, 2026, 10:02 AM",
             "Aug 8, 2026, 08:55 AM", "Aug 22, 2026, 09:30 AM", "Sep 1, 2026, 07:48 AM", "Sep 8, 2026, 08:22 PM"]
RUN_PCT = [2.2, 4.0, 6.1, 8.3, 10.0, 11.8, 13.0, 14.4]
RUN_VERSION = ["v18.0", "v18.0", "v18.1", "v18.1", "v19.0", "v19.0", "v19.1", "v19.1"]

TOP_GAPS = [
    ("T1552.001", "Credentials In Files", "often the fastest path to lateral movement once an attacker has an initial foothold"),
    ("T1219", "Remote Access Software", "used by most ransomware affiliates to keep hands-on-keyboard access"),
    ("T1133", "External Remote Services", "the most common initial-access vector for your declared threat profile"),
    ("T1136.001", "Local Account", "used to establish backup persistence after the initial foothold"),
    ("T1557", "Adversary-in-the-Middle", "can defeat MFA prompts if left undetected"),
]

TOOL_EVAL = {"T1552.001": "Microsoft Defender for Endpoint", "T1219": "Cortex XDR"}

# 12 gap rows: (id, name, tactic, priority[1-4], threat, crown, strength_or_None, feasibility[short/mid/long], via, rec)
GAPS = [
    ("T1552.001", "Credentials In Files", "Credential Access", 1, True, False, None, "short", "EDR (CrowdStrike) file-access telemetry", "Add a rule for bulk reads of files named *password*, *.pem, *id_rsa* by non-admin processes."),
    ("T1219", "Remote Access Software", "Lateral Movement", 1, True, True, None, "mid", None, "Onboard your remote-access tool's own audit log, then alert on unapproved tools (AnyDesk, ScreenConnect) launching."),
    ("T1133", "External Remote Services", "Initial Access", 2, True, False, None, "short", "VPN concentrator logs", "Alert on VPN/Citrix logons from ASNs outside your allow-listed ranges, stacked with the impossible-travel rule."),
    ("T1136.001", "Local Account", "Persistence", 2, False, True, None, "short", "Windows Event Logs", "Alert on local account creation (4720) outside your patch-window change ticket."),
    ("T1557", "Adversary-in-the-Middle", "Defense Evasion", 2, False, False, None, "mid", None, "Onboard DHCP/ARP logs, then alert on unexpected gateway MAC changes or duplicate DHCP servers."),
    ("T1027", "Obfuscated Files or Information", "Defense Evasion", 2, False, False, (48, "Moderate"), "short", "Windows Event Logs (Sysmon)", "Add entropy scoring to Rule 44 instead of keyword-matching only — obfuscated PowerShell rarely contains plain keywords."),
    ("T1598.003", "Spearphishing Link", "Reconnaissance", 3, False, False, (28, "Weak"), "long", None, "Onboard email-gateway click-through telemetry so the existing phishing rule can see whether the link was opened."),
    ("T1595", "Active Scanning", "Reconnaissance", 3, False, False, None, "long", None, "Needs external attack-surface monitoring — no current log source sees pre-attack scanning of your perimeter."),
    ("T1583", "Acquire Infrastructure", "Resource Development", 3, False, False, None, "long", None, "Threat-intel infrastructure correlation (newly-registered domains, bulletproof hosting) is not a capability you own yet."),
    ("T1608", "Stage Capabilities", "Resource Development", 4, False, False, None, "long", None, "No visibility into attacker-side staging; only detectable indirectly once payloads are delivered."),
    ("T1596", "Search Open Technical Databases", "Reconnaissance", 4, False, False, None, "long", None, "Passive OSINT recon against public records — not observable from your own telemetry."),
    ("T1070", "Indicator Removal", "Defense Evasion", 4, False, False, None, "mid", "Windows Event Logs", "Forward Windows event logs to a write-once collector so local log clearing is itself the alert."),
]

ROADMAP = {
    "short": "These build on log sources you already have onboarded — ship them first for the fastest coverage gain.",
    "mid": "Your existing tooling can already provide the telemetry; it just needs a new log source onboarded before the detection can be built.",
    "long": "Nothing you currently own produces this telemetry — treat these as capability investments, not quick wins.",
}

PLATFORMS_RAW = [("Windows", 96, 420), ("Linux", 41, 260), ("ESXi", 3, 40), ("IaaS", 22, 180), ("Containers", 9, 95),
                 ("Office Suite", 14, 60), ("Identity Provider", 18, 55), ("Network Devices", 6, 110),
                 ("Android", 1, 62), ("iOS", 1, 58), ("macOS", 4, 70), ("SaaS", 11, 90)]
PLATFORMS = [{"name": n, "c": c, "a": a, "pct": round(100 * c / a, 1)} for n, c, a in PLATFORMS_RAW]

LOG_SOURCES = [
    {"name": "EDR (CrowdStrike)", "rules": 34, "techs": 61}, {"name": "Windows Event Logs", "rules": 28, "techs": 40},
    {"name": "Windows Event Logs (Sysmon)", "rules": 22, "techs": 35}, {"name": "Entra sign-in logs", "rules": 12, "techs": 9},
    {"name": "Entra audit logs", "rules": 8, "techs": 7}, {"name": "Firewall / NetFlow", "rules": 9, "techs": 6},
    {"name": "EDR (Microsoft Defender for Endpoint)", "rules": 15, "techs": 22}, {"name": "Secure email gateway", "rules": 6, "techs": 5},
    {"name": "VPN concentrator logs", "rules": 4, "techs": 3}, {"name": "Identity provider MFA logs", "rules": 3, "techs": 2},
]

RULES_SAMPLE = [
    {"name": "Rule 12 · Impossible travel sign-in", "status": "customer_tagged", "enabled": True, "source": "Entra sign-in logs", "ref": "Row 14", "techs": [("T1078", "Valid Accounts", 1.0, "Exact technique tag from your file")]},
    {"name": "Rule 141 · VPN from new geo", "status": "ai_tagged", "enabled": True, "source": "VPN concentrator logs", "ref": "Row 88", "techs": [("T1078.004", "Cloud Accounts", 0.62, "AI matched on ‘impossible travel’ plus cloud IdP context")]},
    {"name": "Rule 33 · WAF exploit signature", "status": "keyword_tagged", "enabled": True, "source": "WAF logs", "ref": "Row 22", "techs": [("T1190", "Exploit Public-Facing Application", 1.0, "Rule name references a known CVE exploited via this technique")]},
    {"name": "Rule 4 · Phishing URL click", "status": "customer_tagged", "enabled": True, "source": "Secure email gateway", "ref": "Row 3", "techs": [("T1566", "Phishing", 1.0, "Exact technique tag"), ("T1566.001", "Spearphishing Attachment", 1.0, "Exact technique tag"), ("T1598", "Phishing for Information", 0.7, "Reviewer added this second mapping")]},
    {"name": "Rule 8 · PowerShell encoded command", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs (Sysmon)", "ref": "Row 55", "techs": [("T1059", "Command and Scripting Interpreter", 1.0, "Exact technique tag"), ("T1059.001", "PowerShell", 1.0, "Exact technique tag")]},
    {"name": "Rule 21 · Scheduled task created", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 61", "techs": [("T1053", "Scheduled Task/Job", 1.0, "Exact technique tag"), ("T1005", "Data from Local System", 0.5, "Disabled secondary mapping, lower confidence")]},
    {"name": "Rule 77 · WMI remote exec", "status": "keyword_tagged", "enabled": True, "source": "Windows Event Logs (Sysmon)", "ref": "Row 90", "techs": [("T1047", "Windows Management Instrumentation", 1.0, "Rule logic references wmic.exe / WMI remote execution")]},
    {"name": "Rule 150 · Service installed", "status": "customer_tagged", "enabled": False, "source": "Windows Event Logs", "ref": "Row 101", "techs": [("T1569", "System Services", 1.0, "Exact technique tag")]},
    {"name": "Rule 40 · Account manipulation", "status": "customer_tagged", "enabled": True, "source": "Entra audit logs", "ref": "Row 8", "techs": [("T1098", "Account Manipulation", 1.0, "Exact technique tag"), ("T1087", "Account Discovery", 0.8, "Reviewer added this second mapping")]},
    {"name": "Rule 41 · Local account created", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 9", "techs": [("T1136", "Create Account", 1.0, "Exact technique tag")]},
    {"name": "Rule 62 · Run key added", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs (Sysmon)", "ref": "Row 70", "techs": [("T1547", "Boot or Logon Autostart Execution", 1.0, "Exact technique tag"), ("T1543", "Create or Modify System Process", 0.5, "Disabled rule, lower-confidence secondary mapping")]},
    {"name": "Rule 15 · Process injection (EDR)", "status": "customer_tagged", "enabled": True, "source": "EDR (CrowdStrike)", "ref": "Row 17", "techs": [("T1055", "Process Injection", 1.0, "Exact technique tag")]},
    {"name": "Rule 90 · GPO modified", "status": "ai_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 112", "techs": [("T1484", "Domain or Tenant Policy Modification", 1.0, "Exact technique tag"), ("T1548", "Abuse Elevation Control Mechanism", 0.5, "AI-mapped, confidence 0.5 — spot-check before relying on it")]},
    {"name": "Rule 44 · Obfuscated script block", "status": "keyword_tagged", "enabled": True, "source": "Windows Event Logs (Sysmon)", "ref": "Row 51", "techs": [("T1027", "Obfuscated Files or Information", 0.7, "Rule name references obfuscation, no entropy scoring"), ("T1071", "Application Layer Protocol", 1.0, "Exact technique tag")]},
    {"name": "Rule 2 · Event log cleared", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 2", "techs": [("T1070", "Indicator Removal", 1.0, "Exact technique tag")]},
    {"name": "Rule 132 · Defender disabled", "status": "customer_tagged", "enabled": True, "source": "EDR (Microsoft Defender for Endpoint)", "ref": "Row 140", "techs": [("T1562", "Impair Defenses", 1.0, "Exact technique tag")]},
    {"name": "Rule 152 · Signed binary proxy execution", "status": "customer_tagged", "enabled": True, "source": "EDR (CrowdStrike)", "ref": "Row 149", "techs": [("T1218", "System Binary Proxy Execution", 1.0, "Exact technique tag"), ("T1105", "Ingress Tool Transfer", 0.6, "Reviewer added this second mapping")]},
    {"name": "Rule 1 · LSASS access", "status": "customer_tagged", "enabled": True, "source": "EDR (CrowdStrike)", "ref": "Row 1", "techs": [("T1003", "OS Credential Dumping", 1.0, "Exact technique tag")]},
    {"name": "Rule 9 · Brute force", "status": "customer_tagged", "enabled": True, "source": "Entra sign-in logs", "ref": "Row 11", "techs": [("T1110", "Brute Force", 1.0, "Exact technique tag")]},
    {"name": "Rule 88 · Kerberoasting", "status": "keyword_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 87", "techs": [("T1558", "Steal or Forge Kerberos Tickets", 1.0, "Rule name references Kerberoasting directly")]},
    {"name": "Rule 170 · MFA fatigue", "status": "manual", "enabled": True, "source": "Identity provider MFA logs", "ref": "Row 168", "techs": [("T1621", "Multi-Factor Authentication Request Generation", 1.0, "Edited by reviewer — overrides the original AI tag")]},
    {"name": "Rule 5 · RDP lateral", "status": "customer_tagged", "enabled": True, "source": "Windows Event Logs", "ref": "Row 5", "techs": [("T1021", "Remote Services", 1.0, "Exact technique tag")]},
    {"name": "Rule 139 · Pass-the-hash", "status": "keyword_tagged", "enabled": True, "source": "Windows Event Logs (Sysmon)", "ref": "Row 137", "techs": [("T1550", "Use Alternate Authentication Material", 1.0, "Rule name references pass-the-hash directly")]},
    {"name": "Rule 155 · C2 exfil volume", "status": "ai_tagged", "enabled": True, "source": "Firewall / NetFlow", "ref": "Row 153", "techs": [("T1041", "Exfiltration Over C2 Channel", 0.55, "AI-mapped from a traffic-volume heuristic — spot-check")]},
    {"name": "Rule 173 · Mass file rename/encrypt pattern", "status": "customer_tagged", "enabled": True, "source": "EDR (CrowdStrike)", "ref": "Row 171", "techs": [("T1486", "Data Encrypted for Impact", 1.0, "Exact technique tag"), ("T1490", "Inhibit System Recovery", 1.0, "Exact technique tag")]},
    {"name": "Rule 61 · Legacy proxy signature", "status": "invalid", "enabled": True, "source": "Proxy logs", "ref": "Row 60", "techs": []},
    {"name": "Rule 118 · Custom SOAR alert", "status": "unmapped", "enabled": True, "source": "Custom SOAR playbook", "ref": "Row 116", "techs": []},
    {"name": "Rule 97 · Legacy AV signature", "status": "customer_tagged", "enabled": False, "source": "Legacy AV", "ref": "Row 95", "techs": [("T1204", "User Execution", 1.0, "Exact technique tag, rule since disabled")]},
]

RULE_STATUS_COUNTS = {"customer_tagged": 153, "keyword_tagged": 16, "ai_tagged": 1, "manual": 1, "unmapped": 4, "invalid": 0}
RULE_STATUS_LABEL = {"customer_tagged": "tagged by you", "keyword_tagged": "keyword-matched (no AI)", "ai_tagged": "AI-tagged", "manual": "reviewer-edited", "unmapped": "unmapped", "invalid": "with invalid tags"}

NA_GROUPS = [
    ("Whole matrix not applicable", "These ATT&CK areas don't apply to your environment at all.",
     [("T1490.001", "Reboot (ICS-only availability sub-technique not tracked outside OT)"), ("T1499.003", "Application Exhaustion Flood (no internet-facing service in scope)")]),
    ("Platform not in your environment", "These techniques only work on platforms your inventory doesn't include.",
     [("T1547.009", "Shortcut Modification (mainframe z/OS billing platform has no ATT&CK platform mapping)"), ("T1218.014", "MMC (no environment entry mapped to this platform)")]),
    ("Deprecated by MITRE", "MITRE no longer maintains these techniques, so they aren't assessed.",
     [("T1562.001 (old)", "Disable or Modify Tools — restructured to T1685 in ATT&CK v19.1")]),
    ("Excluded by you", "You asked us not to assess these — each reason is shown exactly as you gave it.",
     [("T1200", "accepted risk, physical controls"), ("mobile: BYOD fleet", "BYOD fleet is unmanaged")]),
]

ASSUMPTIONS = [
    "asset entries not mapped to ATT&CK platforms (ignored for platform filtering): IOT Platform devices (105), Mainframe z/OS billing platform, Microsoft Exchange Server 2019 (hybrid, 4 nodes), …",
    "Consolidated Usecase Tracker:2: MITRE ATT&CK update: tag 'T1562' has been restructured and is now represented under T1685 (Disable or Modify Tools) in ATT&CK v19.1",
    "0 rules matched deterministically by ATT&CK technique or attacker-tool name (no AI involved); 5 sent to AI tagging",
    "1 rules were AI-tagged (confidence ≥ 0.4) — model-generated mappings, spot-check before operational use",
    "4 rules remain unmapped to ATT&CK — they do not count toward coverage",
    "detected columns: description→col 3, enabled→col 12, log_source→col 4, logic→col 8, name→col 2, severity→col 7, tags→col 10",
    "7 detection-strength scores were AI-assessed (optional quality pass) — all others use the deterministic heuristic",
    "gap ranking prioritizes techniques associated with your declared threat profile: " + THREAT_LABELS,
    "2 crown-jewel entries didn't match a known platform/category and were not used for gap prioritization: Telco subscriber billing platform, CyberArk credential vault",
]

GROUPS = [
    {"id": "G0016", "name": "APT29", "aliases": "Cozy Bear, The Dukes", "ids": ["T1078", "T1566", "T1053", "T1003", "T1021"]},
    {"id": "G1015", "name": "Scattered Spider", "aliases": "UNC3944, Muddled Libra", "ids": ["T1566", "T1078.004", "T1552.001", "T1219", "T1621"]},
    {"id": "G0176", "name": "LockBit", "aliases": "LockBit Black", "ids": ["T1486", "T1490", "T1219", "T1133", "T1078"]},
]


def _dom_tactics(tactics):
    return [{"key": key, "name": name, "c": c, "a": a, "cells": cells} for key, name, c, a, cells in tactics]


DATA = {
    "header": {
        "name": "abc ltd", "customer": "Cisco cdc", "attack_version": "v19.1", "prepared_by": "Wipro Practice",
        "project_name": "Cisco CDC SOC", "scope_label": "Global production estate",
        "purpose": "Quarterly detection-coverage review for SOC leadership.", "created": RUN_DATES[-1],
        "conn_name": "abc ltd Sentinel", "conn_workspace": "acme-sec-ops", "conn_rules": 175,
    },
    "runs": [{"date": RUN_DATES[i], "pct": RUN_PCT[i], "version": RUN_VERSION[i]} for i in range(8)],
    "counts": {"covered": 132, "partial": 15, "not_covered": 771, "na": 37, "applicable": 918},
    "domains": {
        "enterprise": {"name": "Enterprise", "c": 125, "a": 697, "pct": 17.9, "tactics": _dom_tactics(ENTERPRISE_TACTICS)},
        "ics": {"name": "ICS / OT", "c": 5, "a": 96, "pct": 5.2, "tactics": _dom_tactics(ICS_TACTICS)},
        "mobile": {"name": "Mobile", "c": 2, "a": 125, "pct": 1.6, "tactics": _dom_tactics(MOBILE_TACTICS)},
    },
    "top_gaps": [{"id": i, "name": n, "hint": h} for i, n, h in TOP_GAPS],
    "gaps": [{"id": i, "name": n, "tactic": t, "pri": p, "threat": thr, "crown": cr,
              "strength": (list(st) if st else None), "feas": fe, "via": vi, "rec": rc}
             for i, n, t, p, thr, cr, st, fe, vi, rc in GAPS],
    "roadmap": ROADMAP,
    "platforms": PLATFORMS,
    "log_sources": LOG_SOURCES,
    "rules": RULES_SAMPLE,
    "rule_status_counts": RULE_STATUS_COUNTS,
    "na_groups": [{"title": t, "blurb": b, "items": [{"key": k, "reason": r} for k, r in items]} for t, b, items in NA_GROUPS],
    "assumptions": ASSUMPTIONS,
    "groups": GROUPS,
    "tool_eval": TOOL_EVAL,
    "tools_label": "Defender for Endpoint and Cortex XDR",
    "tool_overlay": {"tool": "Microsoft Defender for Endpoint", "n": 15, "rules_n": 117, "rules_pct": 12.7, "tools_pct": 1.6, "adjusted_pct": 14.4, "extra": 9},
    "state_tip": STATE_TIP, "state_label": STATE_LABEL, "state_plain": STATE_PLAIN, "rule_status_label": RULE_STATUS_LABEL,
}

# ==================================================================== markup: header
def _export_btn(key, icon_name, label):
    return T('<button class="btn sm tip {{h.exp.[[k]].cls}}" data-tip="{{h.exp.[[k]].tip}}" onClick="{{h.exp.[[k]].click}}">[[ico]] [[label]]</button>',
              k=key, ico=icon(icon_name, 14), label=esc(label))


RUN_BLOCK_RUNNING = T("""<div class="alert info row rise" style="align-items:flex-start;gap:10px;margin-bottom:14px">[[sp]]<div><b>Assessing your coverage…</b><div style="margin-top:4px">We're mapping rules to techniques, filtering to your environment, and computing the results. Untagged rules go through AI tagging, so this can take a few minutes. The page refreshes itself.</div></div></div>""", sp=icon("loader", 18, cls="spin"))
RUN_BLOCK_FAILED = T("""<div class="alert err row rise" style="align-items:flex-start;gap:10px;margin-bottom:14px"><div class="grow"><b>This run didn't finish.</b><div style="margin-top:4px">The connection to your SIEM timed out while pulling rules. Nothing was scored.</div></div>[[b]]</div>""", b=btn("Re-run assessment", "danger", "rotate", "sm"))
RUN_BLOCK_PENDING = T("""<div class="alert warn row rise" style="align-items:flex-start;gap:10px;margin-bottom:14px"><div class="grow">This assessment is uploaded and parsed, but hasn't been run yet.</div>[[b]]</div>""", b=btn("Run assessment", "primary", "play", "sm"))

HEADER = T("""
<div class="pagehead" style="margin-bottom:8px">
  <div class="row wrap" style="gap:10px;align-items:center">
    <span style="color:var(--accent)">[[target]]</span>
    <h1>{{h.name}}</h1>
    <sc-if value="{{h.demo}}" hint-placeholder-val="{{true}}">[[demo]]</sc-if>
    <span class="chip {{h.statusTone}}">{{h.statusLabel}}</span>
  </div>
  <div class="actions" style="align-items:center">
    <sc-if value="{{h.showRuns}}" hint-placeholder-val="{{true}}">
    <span class="rel">
      <button class="btn sm" aria-haspopup="listbox" aria-label="Past assessment runs" onClick="{{h.runsToggle}}">[[hist]] Past runs ({{h.runsN}})</button>
      <div class="menu {{h.runsCls}}" role="listbox" aria-label="Past assessment runs" style="min-width:308px;right:0">
        <sc-for list="{{h.runRows}}" as="rr" hint-placeholder-count="8">
          <div class="row between" style="padding:7px 8px;border-radius:6px;gap:8px">
            <div class="grow" style="min-width:0"><div style="font-size:13px;font-weight:{{rr.w}};color:{{rr.color}}">{{rr.label}}</div>
              <div class="faint num" style="font-size:11.5px">{{rr.date}} · {{rr.pct}}% <span style="color:{{rr.dcolor}}">{{rr.delta}}</span></div></div>
            <button class="btn ghost sm" style="height:24px;padding:0 8px;font-size:11.5px" onClick="{{rr.compare}}">Compare</button>
          </div>
        </sc-for>
      </div>
    </span>
    </sc-if>
    [[be]][[bf]][[bx]][[bp]][[bn]]
    <span class="faint num" style="font-size:12px" data-hide-phone="1">created {{h.created}}</span>
  </div>
</div>
<sc-if value="{{h.running}}" hint-placeholder-val="{{false}}">[[rb1]]</sc-if>
<sc-if value="{{h.failed}}" hint-placeholder-val="{{false}}">[[rb2]]</sc-if>
<sc-if value="{{h.pending}}" hint-placeholder-val="{{false}}">[[rb3]]</sc-if>
<div class="sub" style="font-size:12.5px;margin-bottom:3px">{{h.metaLine}}</div>
<div class="faint" style="font-size:12px;margin-bottom:16px">{{h.siemLine}}</div>
""", target=icon("target", 20), demo=chip("Demo", "info", tip="Shared sample assessment — read-only for everyone"),
    hist=icon("history", 14),
    be=_export_btn("execpdf", "file-down", "Exec PDF"), bf=_export_btn("fullpdf", "file-down", "Full PDF"),
    bx=_export_btn("xlsx", "file-spreadsheet", "XLSX"), bp=_export_btn("ppt", "presentation", "PPT"), bn=_export_btn("nav", "file-json", "Navigator"),
    rb1=RUN_BLOCK_RUNNING, rb2=RUN_BLOCK_FAILED, rb3=RUN_BLOCK_PENDING)

# ==================================================================== markup: executive band
KPI_KEYS = ["coverage", "enterprise", "ics", "mobile", "covered", "partial", "notcovered", "na"]
EXEC_BAND = T("""
<div class="grid g8" style="gap:10px;margin-bottom:14px">
  <sc-for list="{{kpis}}" as="k" hint-placeholder-count="8">
    <button class="kpi click tip" data-tip="{{k.tip}}" onClick="{{k.open}}"><span class="lbl">{{k.label}}</span><span class="v num" style="color:{{k.color}}">{{k.value}}</span><span class="faint" style="font-size:12px">{{k.sub}}</span></button>
  </sc-for>
</div>
<div class="row wrap" style="gap:8px;align-items:center;margin-bottom:10px">
  <span style="font-size:13px">{{headline}} <button class="tip" style="background:none;border:0;padding:0;border-bottom:1px dotted var(--ink3);color:var(--ink2);cursor:pointer;font-size:13px" data-tip="Probably not as bad as it looks: early SIEM detection programs typically start under 10% strict coverage, because ATT&CK counts every known attacker technique. The point of this assessment is the roadmap — the short-term items raise this number fastest — not the grade itself.">Is {{pct}}% bad?</button></span>
</div>
<div class="row wrap" style="gap:8px;align-items:center;justify-content:space-between;margin-bottom:16px">
  <div class="row wrap" style="gap:6px"><span class="faint" style="font-size:12.5px">Top gaps:</span>
    <sc-for list="{{topGaps}}" as="g" hint-placeholder-count="5"><button class="chip crit tip" data-tip="{{g.tip}}" onClick="{{g.open}}">{{g.id}}</button></sc-for>
  </div>
  <span class="faint num" style="font-size:12px">ATT&amp;CK {{version}} · run {{bandRunDate}}</span>
</div>""")

# ==================================================================== markup: tool overlay banner
TOOL_BANNER = T("""
<div class="alert blue rise" style="margin-bottom:14px">
  <div class="row wrap" style="gap:10px;align-items:flex-start;justify-content:space-between">
    <div class="grow">
      <div><b>Including {{tools}}'s MITRE-evaluated detections: {{adjPct}}%</b></div>
      <div class="faint" style="margin-top:2px">({{extra}} open techniques those tools were evaluated against · Vendor-evaluated in MITRE ATT&CK Evaluations — not proof the alerts are tuned, monitored, or reaching your SOC. Source: evals.mitre.org)</div>
      <div style="margin-top:6px">Combined covered {{combN}} = {{rulesN}} by SIEM rules ({{rulesPct}}%) + {{toolsN}} via attested tools ({{toolsPct}}%)</div>
    </div>
    <button class="btn sm tip" data-tip="Records that your SOC receives and monitors this tool's alerts, creates one auditable rule per technique, and recomputes coverage." onClick="{{attestOpen}}">{{attestLabel}}</button>
  </div>
</div>""")

ATTEST_DLG = dialog("attest", "Attest tool-evaluated coverage", '<p>{{attestQ}}</p><p style="margin-top:8px">{{attestBody}}</p>',
                     btn("Cancel", "", size="sm", attrs='onClick="{{dlg.attest.close}}"') + btn("{{attestConfirmLabel}}", "primary", size="sm", attrs='onClick="{{attestConfirm}}"'), 460)

# ==================================================================== markup: upload summary card
UPLOAD_CARD = T("""
<div class="card rise" style="margin-bottom:16px">
  <div class="card-h"><h3>What this assessment is based on</h3></div>
  <div class="card-b grid g2" style="gap:20px">
    <div>
      <div class="row" style="gap:8px">[[fs]]<span style="font-weight:600">{{rulesFile}}</span><button class="chip blue xs tip" data-tip="All {{rulesTotal}} rules" onClick="{{openAllRules}}">{{rulesTotal}} rules</button></div>
      <div class="row wrap" style="gap:6px;margin-top:8px">
        <sc-for list="{{statusChips}}" as="s" hint-placeholder-count="6"><button class="chip {{s.tone}} xs tip" data-tip="{{s.tip}}" onClick="{{s.open}}">{{s.label}}</button></sc-for>
      </div>
      <div class="faint" style="font-size:12px;margin-top:10px">asset entries not mapped to ATT&amp;CK platforms (ignored for platform filtering): IOT Platform devices (105), Mainframe z/OS billing platform, Microsoft Exchange Server 2019 (hybrid, 4 nodes), …</div>
      <button class="btn ghost sm" style="margin-top:8px;padding-left:2px" onClick="{{invToggle}}"><span style="display:inline-flex;transition:transform .15s;transform:{{invRot}}">[[chev3]]</span>How we read your inventory ({{invCount}} entries)</button>
      <sc-if value="{{invOpen}}" hint-placeholder-val="{{false}}">
        <div class="stack" style="gap:6px;margin-top:8px;font-size:12.5px" class="sub">
          <sc-for list="{{invRows}}" as="ir" hint-placeholder-count="4"><div><b>{{ir.entry}}</b> ({{ir.sheet}}) → {{ir.interp}}</div></sc-for>
        </div>
      </sc-if>
    </div>
    <div>
      <div class="row" style="gap:8px">[[fs2]]<span style="font-weight:600">{{envFile}}</span>[[otchip]][[mobchip]]</div>
      <div class="sub" style="font-size:12.5px;margin-top:8px">Platforms: {{platformList}} · <button class="btn link tip" style="font-size:12.5px" data-tip="See what each log source actually detects for you" onClick="{{srcToggle}}">{{srcCount}} log source(s)</button> · {{toolingN}} tooling · {{crownN}} crown jewel(s)</div>
      <sc-if value="{{srcOpen}}" hint-placeholder-val="{{false}}">
        <div class="row wrap" style="gap:6px;margin-top:8px">
          <sc-for list="{{srcChips}}" as="lc" hint-placeholder-count="8"><button class="chip outline xs tip" data-tip="Open the rules mapped from {{lc.name}}" onClick="{{lc.open}}">{{lc.label}}</button></sc-for>
        </div>
      </sc-if>
    </div>
  </div>
</div>""", fs=icon("file-spreadsheet", 18), fs2=icon("file-spreadsheet", 18),
    otchip=chip("OT/ICS", "grey", xs=True), mobchip=chip("Managed mobile", "grey", xs=True), chev3=icon("chevron-right", 13))

# ==================================================================== markup: tab bar + search
TAB_BAR = T("""
<div class="row between wrap" style="gap:12px;margin-bottom:14px;align-items:center">
  [[tabs]]
  <div class="row" style="gap:8px;align-items:center">
    <div class="search" style="width:280px">[[si]]<input class="input sm" type="search" placeholder="Is it covered? Try 'T1486', 'ransomware', 'linux', 'APT29'…" aria-label="Search techniques, attack stages, platforms, threat groups and rules" value="{{q}}" onChange="{{setQ}}" onKeyDown="{{qKey}}"></div>
    <button class="btn ghost icon sm tip" data-tip="Search anything — a technique ID or name, an attack stage, a platform/asset type, a threat group, or one of your rules — and see its coverage state instantly." aria-label="Search this assessment" onClick="{{qSearch}}">[[si2]]</button>
    <sc-if value="{{tabsShowExport}}" hint-placeholder-val="{{true}}">
      <button class="btn ghost icon sm tip" data-tip="Download only this tab as PDF" aria-label="Download only this tab as PDF">[[pdfi]]</button>
      <button class="btn ghost icon sm tip" data-tip="Download only this tab as Excel" aria-label="Download only this tab as Excel">[[xlsi]]</button>
    </sc-if>
  </div>
</div>""", tabs=tabs("t", [("coverage", "Coverage"), ("gaps", "Gaps &amp; Roadmap"), ("assumptions", "Assumptions &amp; N/A"), ("compare", "Compare")]).replace('role="tablist"', 'role="tablist" aria-label="Assessment result views"'),
    si=icon("search", 14), si2=icon("search", 15), pdfi=icon("file-down", 15), xlsi=icon("file-spreadsheet", 15))

# ==================================================================== markup: coverage tab
FILTER_BAR = T("""
<div class="row wrap" style="gap:10px;align-items:center;margin-bottom:10px">
  <label class="row" style="gap:6px;font-size:13px">Threat group:
    <select class="select sm" aria-label="Threat group" value="{{group}}" onChange="{{setGroup}}" style="min-width:170px">
      <option value="">None — full matrix</option>
      <sc-for list="{{groupOpts}}" as="go" hint-placeholder-count="3"><option value="{{go.id}}">{{go.label}}</option></sc-for>
    </select>
  </label>
  <span class="rel">
    <button class="btn sm" aria-haspopup="menu" onClick="{{runsOnToggle}}">Runs on{{runsOnSuffix}} [[chev]]</button>
    <div class="menu {{runsOnCls}}" role="menu" style="min-width:260px">
      <div class="faint" style="padding:6px 8px;font-size:11.5px">Show only techniques that can run on… (% = coverage there)</div>
      <div style="padding:0 6px 6px"><input class="input sm" style="width:100%" placeholder="Search platforms…" aria-label="Search platforms…" value="{{platformSearch}}" onChange="{{setPlatformSearch}}"></div>
      <button onClick="{{runsOnClear}}">Clear — all platforms</button>
      <sc-for list="{{platformItems}}" as="pi" hint-placeholder-count="10">
        <button onClick="{{pi.toggle}}"><input type="checkbox" checked="{{pi.on}}" style="pointer-events:none" tabindex="-1"><span class="grow" style="text-align:left">{{pi.name}}</span><span class="faint num" style="font-size:11.5px">{{pi.c}}/{{pi.a}} · {{pi.pct}}%</span></button>
      </sc-for>
    </div>
  </span>
  <span class="rel">
    <button class="btn sm" aria-haspopup="menu" onClick="{{detViaToggle}}">Detected via{{detViaSuffix}} [[chev2]]</button>
    <div class="menu {{detViaCls}}" role="menu" style="min-width:260px">
      <div class="faint" style="padding:6px 8px;font-size:11.5px">Show only what a log source's rules detect</div>
      <div style="padding:0 6px 6px"><input class="input sm" style="width:100%" placeholder="Search sources…" aria-label="Search sources…" value="{{sourceSearch}}" onChange="{{setSourceSearch}}"></div>
      <button onClick="{{detViaClear}}">Clear — all sources</button>
      <sc-for list="{{sourceItems}}" as="si" hint-placeholder-count="10">
        <button onClick="{{si.toggle}}"><input type="checkbox" checked="{{si.on}}" style="pointer-events:none" tabindex="-1"><span class="grow" style="text-align:left">{{si.name}}</span><span class="faint num" style="font-size:11.5px">{{si.n}} rule(s)</span></button>
      </sc-for>
    </div>
  </span>
  <sc-if value="{{hasGroup}}" hint-placeholder-val="{{false}}"><span class="faint" style="font-size:12.5px">{{groupStats}}</span></sc-if>
  <button class="btn ghost sm tip" style="margin-left:auto" data-tip="CSV of exactly the techniques currently shown — your threat-group, platform, log-source and state filters all apply. The report buttons above always export the full assessment." onClick="{{downloadShown}}">[[dl]] Download shown ({{shownN}})</button>
</div>
<div class="sub" style="font-size:12.5px;margin-bottom:10px">{{lensSentence}}</div>
""", chev=icon("chevron-down", 13), chev2=icon("chevron-down", 13), dl=icon("download", 13))

LEGEND = T("""
<div class="row wrap" style="gap:8px;align-items:center;margin-bottom:12px">
  <button class="chip tip" aria-pressed="{{lgCov.p}}" style="opacity:{{lgCov.op}};background:linear-gradient(90deg,#BFE1CB,var(--ok) 55%,#1E5C36);color:#fff" data-tip="{{lgCov.tip}}" onClick="{{lgCov.toggle}}">Covered</button>
  <button class="chip med tip" aria-pressed="{{lgPar.p}}" style="opacity:{{lgPar.op}}" data-tip="{{lgPar.tip}}" onClick="{{lgPar.toggle}}">Partial</button>
  <button class="chip crit tip" aria-pressed="{{lgNo.p}}" style="opacity:{{lgNo.op}}" data-tip="{{lgNo.tip}}" onClick="{{lgNo.toggle}}">Not covered</button>
  <button class="chip grey tip" aria-pressed="{{lgNa.p}}" style="opacity:{{lgNa.op}}" data-tip="{{lgNa.tip}}" onClick="{{lgNa.toggle}}">N/A</button>
  <sc-if value="{{legendFiltered}}" hint-placeholder-val="{{false}}"><button class="btn link" style="font-size:12.5px" onClick="{{showAll}}">Show all</button></sc-if>
  <button class="btn ghost sm tip" aria-pressed="{{hideSubsPressed}}" data-tip="Collapse the matrix to parent techniques only — each parent shows how many of its sub-techniques are covered. Coverage counts don't change." onClick="{{toggleHideSubs}}">{{hideSubsLabel}}</button>
  <span class="faint" style="font-size:12px">Click any technique for details.</span>
</div>
""")

RUN_TIMELINE = T("""
<div class="card rise" style="padding:14px 16px;margin-bottom:14px">
  <div class="row wrap" style="gap:16px;align-items:center">
    <div class="tip" data-tip="Covered techniques divided by applicable techniques for the run shown below. N/A techniques leave the denominator with a printed reason." style="min-width:130px">
      <div class="lbl">Coverage · run {{runNum}}</div>
      <div class="num" style="font-size:28px;font-weight:600">{{runPct}}%</div>
      <div class="faint" style="font-size:11.5px">{{runDate}} · <span style="color:{{runDeltaColor}}">{{runDelta}}</span></div>
    </div>
    <div class="grow" style="min-width:220px">
      <div class="row between faint" style="font-size:11.5px;margin-bottom:4px"><span>{{firstDate}}</span><span>{{lastDate}}</span></div>
      <input type="range" min="0" max="7" value="{{run}}" onInput="{{onSlide}}" onChange="{{onSlide}}" aria-label="Run timeline">
      <div class="row between" style="margin-top:6px">
        <sc-for list="{{ticks}}" as="tk" hint-placeholder-count="8"><span class="tip" data-tip="{{tk.tip}}" onClick="{{tk.pick}}" style="width:9px;height:9px;border-radius:999px;background:{{tk.bg}};cursor:pointer;transform:{{tk.scale}};transition:background .3s,transform .2s"></span></sc-for>
      </div>
    </div>
    <button class="btn sm" onClick="{{togglePlay}}">[[pi]] {{playLabel}}</button>
  </div>
</div>""", pi=icon("play", 13))

DOMAIN_SECTION = T("""
<div class="card rise" style="margin-bottom:14px;overflow:hidden">
  <div class="row" style="gap:8px;padding:10px 14px;border-bottom:1px solid var(--line);background:#FBFAF8">
    <button class="xbtn" aria-expanded="{{d.open}}" aria-label="{{d.toggleAria}}" onClick="{{d.toggle}}"><span style="display:inline-flex;transition:transform .15s;transform:{{d.rot}}">[[chev]]</span></button>
    <span style="font-weight:600;font-size:13.5px">{{d.name}}</span>
    <button class="btn link" style="font-size:12.5px" onClick="{{d.drill}}">— {{d.c}}/{{d.a}} covered ({{d.pct}}%){{d.filterSuffix}}</button>
  </div>
  <sc-if value="{{d.open}}" hint-placeholder-val="{{true}}">
  <div style="padding:14px;overflow-x:auto">
    <div style="display:grid;grid-template-columns:repeat({{d.ncols}},minmax(148px,1fr));gap:10px;min-width:max-content">
      <sc-for list="{{d.tactics}}" as="t" hint-placeholder-count="6">
        <div style="min-width:0">
          <button class="btn ghost sm tip" style="width:100%;justify-content:space-between;padding:0 4px;height:26px;font-weight:600;font-size:12px" data-tip="{{t.tip}}" onClick="{{t.drill}}"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{t.name}}</span><span class="num faint" style="font-weight:500">{{t.count}}</span></button>
          <div class="stack" style="gap:4px;margin-top:6px">
            <sc-for list="{{t.rows}}" as="c" hint-placeholder-count="6">
              <button class="tip" data-tid="{{c.id}}" data-tip="{{c.tip}}" onClick="{{c.open}}" style="text-align:left;border:1px solid {{c.border}};background:{{c.bg}};color:{{c.fg}};opacity:{{c.op}};border-radius:6px;padding:5px 7px;margin-left:{{c.indent}};font-size:11px;line-height:1.35;transition:background .4s,opacity .2s;cursor:pointer;display:block;width:calc(100% - {{c.indent}})">
                <b class="mono">{{c.id}}</b> {{c.name}}{{c.badge}}
              </button>
            </sc-for>
          </div>
        </div>
      </sc-for>
    </div>
  </div>
  </sc-if>
</div>""", chev=icon("chevron-right", 14))

COVERAGE_TAB = T("[[filter]][[legend]][[timeline]]<sc-for list=\"{{domainList}}\" as=\"d\" hint-placeholder-count=\"3\">[[sec]]</sc-for>",
                  filter=FILTER_BAR, legend=LEGEND, timeline=RUN_TIMELINE, sec=DOMAIN_SECTION)

# ==================================================================== markup: gaps & roadmap tab
GAPS_COLS = "40px minmax(0,1.7fr) minmax(0,1fr) minmax(0,1.15fr) minmax(0,.9fr) minmax(0,1.35fr) minmax(0,2fr)"
GAPS_HEAD = T('<div class="dr dh" style="grid-template-columns:[[cols]]">[[h1]][[h2]][[h3]][[h4]][[h5]][[h6]][[h7]]</div>', cols=GAPS_COLS,
              h1=dth("gaps", "rank", "#", "r", tip="Sort by rank"),
              h2=dth("gaps", "name", "Technique"),
              h3=dth("gaps", "tactic", "Tactic", sortable=False),
              h4=dth("gaps", "pri", "Priority", tip="How commonly attackers use this technique in real intrusions, from independent threat reports: P1 near-universal, P2 very common, P3 common. A violet dot means it is also tied to your declared industry or threat actors."),
              h5=dth("gaps", "strength", "Strength"),
              h6=dth("gaps", "feas", "Feasibility", tip="How soon you could realistically build this detection: build now = the needed logs are already onboarded; onboard first = your existing tooling can provide them; new capability = nothing you own produces this telemetry yet."),
              h7=dth("gaps", "rec", "Recommendation", sortable=False))
GAPS_ROW = T("""<div class="dr" style="grid-template-columns:[[cols]]">[[c1]][[c2]][[c3]][[c4]][[c5]][[c6]][[c7]]</div>""", cols=GAPS_COLS,
             c1=dcell("#", "{{r.rank}}", "r"),
             c2=dcell("Technique", '<button class="btn link mono" style="font-size:12.5px;padding:0;height:auto" onClick="{{r.open}}">{{r.id}}</button> {{r.name}}'),
             c3=dcell("Tactic", "{{r.tactic}}"),
             c4=dcell("Priority", T('<span class="row" style="gap:6px;flex-wrap:wrap"><i class="dot" style="background:{{r.priColor}}"></i>{{r.priLabel}}'
                                     '<sc-if value="{{r.threat}}" hint-placeholder-val="{{false}}"><span class="tip" style="color:var(--violet);font-weight:700" data-tip="Prioritized for your declared threat profile ([[tl]]): these threats are publicly reported to use this technique. Affects ordering only — never the coverage score.">▲</span></sc-if>'
                                     '<sc-if value="{{r.crown}}" hint-placeholder-val="{{false}}"><span class="tip" style="color:var(--high);font-weight:700" data-tip="Relevant to an asset you declared as a crown jewel. Affects ordering only — never the coverage score.">♦</span></sc-if></span>', tl=THREAT_LABELS)),
             c5=dcell("Strength", "{{r.strengthText}}"),
             c6=dcell("Feasibility", '<span class="row" style="gap:6px"><i class="dot" style="background:{{r.feasColor}}"></i>{{r.feasLabel}}</span><div class="faint" style="font-size:11px">{{r.viaLine}}</div>'),
             c7=dcell("Recommendation", '<span style="font-size:12.5px">{{r.rec}}</span>'))
GAPS_TABLE = T('<div class="dt">[[head]]<sc-for list="{{gaps.rows}}" as="r" hint-placeholder-count="12">[[row]]</sc-for></div>', head=GAPS_HEAD, row=GAPS_ROW)

GAPS_TAB = T("""
<div class="row wrap" style="gap:10px;align-items:center;margin-bottom:12px">
  <h2 style="font-size:16px">Gaps, ranked by priority</h2>
  <span class="chip {{aiTone}} xs tip" data-tip="{{aiTip}}">{{aiLabel}}</span>
</div>
[[table]]
<sc-if value="{{hasMore}}" hint-placeholder-val="{{true}}"><button class="btn link" style="margin-top:10px" onClick="{{toggleAll}}">{{showAllLabel}}</button></sc-if>
<div class="grid g3" style="gap:12px;margin-top:20px">
  <sc-for list="{{roadmap}}" as="rm" hint-placeholder-count="3">
    <div class="card" style="padding:14px">
      <div class="row between"><h3 style="font-size:14px">{{rm.label}}</h3><span class="faint num" style="font-size:12px">{{rm.window}}</span></div>
      <div class="faint num" style="font-size:12px;margin:2px 0 8px">{{rm.count}} item(s)</div>
      <p class="sub" style="font-size:12.5px">{{rm.narrative}}</p>
      <sc-if value="{{rm.hasItems}}" hint-placeholder-val="{{true}}">
        <div class="stack" style="gap:4px;margin-top:8px">
          <sc-for list="{{rm.items}}" as="it" hint-placeholder-count="4"><button class="btn link" style="font-size:12.5px;justify-content:flex-start" onClick="{{it.open}}">{{it.id}} {{it.name}}</button></sc-for>
        </div>
      </sc-if>
      <sc-if value="{{rm.empty}}" hint-placeholder-val="{{false}}"><p class="faint" style="font-size:12.5px;margin-top:8px">Nothing in this bucket.</p></sc-if>
    </div>
  </sc-for>
</div>""", table=GAPS_TABLE)

# ==================================================================== markup: assumptions & N/A tab
ASSUMPTIONS_TAB = T("""
<h2 style="font-size:16px;margin-bottom:4px">Assumptions made in this assessment</h2>
<p class="sub" style="font-size:13px;margin-bottom:10px">Read these before trusting the numbers — they describe what we had to assume or could not verify.</p>
<div class="row wrap" style="gap:6px;align-items:center;margin-bottom:10px">
  <span class="faint" style="font-size:12.5px">Your {{rulesTotal}} rules:</span>
  <sc-for list="{{ruleChips}}" as="rc" hint-placeholder-count="6"><button class="chip {{rc.tone}} xs tip" data-tip="{{rc.tip}}" onClick="{{rc.open}}">{{rc.label}}</button></sc-for>
  <span class="chip violet xs tip" data-tip="Your declared industry and threat actors lifted these within their priority tier — ordering only, never the coverage score.">{{threatMatches}} threat-profile matches</span>
</div>
<div class="grid g2" style="gap:6px 20px;margin-bottom:22px">
  <sc-for list="{{assumptions}}" as="a" hint-placeholder-count="9"><div class="sub" style="border-left:2px solid var(--line2);padding:2px 0 2px 10px;font-size:12.5px">{{a}}</div></sc-for>
  <sc-if value="{{assumptionsEmpty}}" hint-placeholder-val="{{false}}"><p class="sub">No assumptions were needed.</p></sc-if>
</div>
<h2 style="font-size:16px;margin-bottom:4px">Not-applicable techniques ({{naTotal}})</h2>
<p class="sub" style="font-size:13px;margin-bottom:10px">These leave the coverage denominator — the headline percentage makes no claim about them. Grouped by reason; click any technique for its details.</p>
<div class="grid g2" style="gap:12px">
  <sc-for list="{{naGroups}}" as="ng" hint-placeholder-count="4">
    <div class="card" style="padding:12px 14px">
      <div class="row between"><h3 style="font-size:13.5px">{{ng.title}}</h3><button class="btn link" style="font-size:12.5px" onClick="{{ng.drill}}">{{ng.n}} techniques</button></div>
      <p class="faint" style="font-size:12px;margin:4px 0 8px">{{ng.blurb}}</p>
      <div class="row wrap" style="gap:6px">
        <sc-for list="{{ng.items}}" as="it" hint-placeholder-count="2"><button class="chip outline xs tip" data-tip="{{it.tip}}" onClick="{{it.open}}">{{it.label}}</button></sc-for>
      </div>
    </div>
  </sc-for>
</div>""")

# ==================================================================== markup: compare tab
COMPARE_LIST = T("""<sc-if value="{{l.empty}}" hint-placeholder-val="{{false}}"><span class="faint" style="font-size:12.5px">None.</span></sc-if>
<div class="stack" style="gap:4px"><sc-for list="{{l.rows}}" as="x" hint-placeholder-count="2"><button class="btn ghost" style="justify-content:flex-start;height:auto;padding:3px 6px;font-size:12.5px;text-align:left" onClick="{{x.open}}">{{x.id}} {{x.name}} <span class="faint" style="margin-left:6px">{{x.change}}</span></button></sc-for></div>""")

COMPARE_TAB = T("""
<div class="row" style="gap:10px;align-items:center;margin-bottom:14px">
  <label class="row" style="gap:6px;font-size:13px">Compare with
    <select class="select sm" aria-label="Compare with" value="{{cmpWith}}" onChange="{{setCmp}}" style="min-width:280px">
      <option value="">Select an earlier completed run…</option>
      <sc-for list="{{cmpOpts}}" as="co" hint-placeholder-count="7"><option value="{{co.idx}}">{{co.label}}</option></sc-for>
    </select>
  </label>
</div>
<sc-if value="{{cmpLoading}}" hint-placeholder-val="{{false}}"><p class="sub">Comparing…</p></sc-if>
<sc-if value="{{cmpErr}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert">Comparison failed</p></sc-if>
<sc-if value="{{cmpEmpty}}" hint-placeholder-val="{{true}}"><p class="sub" style="padding:24px 0">Nothing to compare against yet — run a second assessment later to see your coverage trend.</p></sc-if>
<sc-if value="{{cmpHas}}" hint-placeholder-val="{{false}}">
<div class="rise">
  <h2 style="font-size:16px;margin-bottom:8px">{{cmpHeader}}</h2>
  <sc-if value="{{cmpMismatch}}" hint-placeholder-val="{{false}}"><div class="alert warn" style="margin-bottom:12px">These runs used different ATT&amp;CK versions ({{cmpVerA}} vs {{cmpVerB}}) — techniques that exist in only one version are left out of this comparison.</div></sc-if>
  <div class="grid g5" style="gap:10px;margin-bottom:16px">
    <sc-for list="{{deltaChips}}" as="dch" hint-placeholder-count="5">
      <div class="card tip" data-tip="{{dch.tip}}" style="padding:10px 12px"><div class="lbl">{{dch.label}}</div><div class="num" style="font-size:20px;font-weight:600;color:{{dch.color}}">{{dch.value}}</div></div>
    </sc-for>
  </div>
  <div style="margin-bottom:16px"><div class="lbl" style="margin-bottom:6px">Tactics that moved</div>
    <sc-if value="{{tacticsEmpty}}" hint-placeholder-val="{{false}}"><span class="faint" style="font-size:12.5px">No per-tactic changes.</span></sc-if>
    <div class="row wrap" style="gap:6px"><sc-for list="{{tacticMoves}}" as="tm" hint-placeholder-count="3"><span class="chip outline xs tip" data-tip="{{tm.tip}}">{{tm.label}}</span></sc-for></div>
  </div>
  <div class="grid g3" style="gap:14px">
    <div><div class="lbl" style="margin-bottom:6px">Newly covered</div><p class="faint" style="font-size:11.5px;margin-bottom:6px">Techniques you can detect now but couldn't in the older run.</p>[[l1]]</div>
    <div><div class="lbl" style="margin-bottom:6px">Regressed</div><p class="faint" style="font-size:11.5px;margin-bottom:6px">Covered in the older run but not now — e.g. a rule was disabled or removed.</p>[[l2]]</div>
    <div><div class="lbl" style="margin-bottom:6px">N/A changed</div><p class="faint" style="font-size:11.5px;margin-bottom:6px">Techniques that entered or left the applicable set — usually an environment or scope-exclusion change, not a detection change.</p>[[l3]]</div>
  </div>
</div>
</sc-if>""", l1=COMPARE_LIST.replace("{{l.", "{{l1.").replace('list="{{l1.rows}}"', 'list="{{l1.rows}}"'),
    l2=COMPARE_LIST.replace("{{l.", "{{l2."), l3=COMPARE_LIST.replace("{{l.", "{{l3."))

# ==================================================================== dialogs + sheets
ATTEST_DLG = dialog("attest", "Attest tool-evaluated coverage", '<p>{{attestQ}}</p><p style="margin-top:8px">{{attestBody}}</p>',
                     btn("Cancel", "", size="sm", attrs='onClick="{{dlg.attest.close}}"') + btn("{{attestConfirmLabel}}", "primary", size="sm", attrs='onClick="{{attestConfirm}}"'), 460)

DRILL_GROUP = T("""
<div style="margin-bottom:14px">
  <div class="lbl" style="margin-bottom:6px">{{g.label}} ({{g.n}})</div>
  <div class="stack" style="gap:2px">
    <sc-for list="{{g.rows}}" as="r" hint-placeholder-count="3">
      <button class="btn ghost" style="justify-content:flex-start;height:auto;padding:6px 8px;text-align:left;gap:8px" onClick="{{r.open}}">
        <i class="dot" style="background:{{r.color}};margin-top:5px;flex:none"></i>
        <span class="grow" style="min-width:0"><span style="font-weight:600">{{r.id}}</span> {{r.name}}<div class="faint" style="font-size:11.5px;font-weight:400">{{r.sub}}</div></span>
      </button>
    </sc-for>
  </div>
</div>""")
DRILL_BODY = T('<sc-for list="{{drillGroups}}" as="g" hint-placeholder-count="4">[[grp]]</sc-for><sc-if value="{{drillEmpty}}" hint-placeholder-val="{{false}}"><p class="empty">Nothing to show here.</p></sc-if>', grp=DRILL_GROUP)
DRILL_SHEET = sheet("drill", '<h2 style="font-size:16px">{{drillTitle}}</h2><p class="sub" style="font-size:12.5px">{{drillSubtitle}}</p>', DRILL_BODY, "", aria="Technique drill-down")

RULE_CARD = T("""
<div class="card" style="padding:10px 12px;margin-bottom:8px;box-shadow:none">
  <div style="font-weight:600;font-size:13px">{{r.name}}</div>
  <div class="faint" style="font-size:11.5px;margin-top:2px">{{r.meta}}</div>
  <sc-if value="{{r.hasMaps}}" hint-placeholder-val="{{true}}">
    <div class="stack" style="gap:4px;margin-top:8px">
      <sc-for list="{{r.maps}}" as="mp" hint-placeholder-count="2">
        <div class="row wrap" style="gap:6px;font-size:12px"><button class="chip blue xs" onClick="{{mp.open}}">{{mp.id}}</button><span class="faint">{{mp.sourceLabel}} at {{mp.pct}}% confidence — {{mp.rationale}}</span></div>
      </sc-for>
    </div>
  </sc-if>
</div>""")
RULES_BODY = T('<sc-for list="{{ruleRows}}" as="r" hint-placeholder-count="6">[[card]]</sc-for><sc-if value="{{rulesEmpty}}" hint-placeholder-val="{{false}}"><p class="empty">No rules in this group.</p></sc-if><p class="faint" style="font-size:11.5px;margin-top:10px">Showing the first 500 rules only — the XLSX export holds everything.</p>', card=RULE_CARD)
RULES_SHEET = sheet("rules", '<h2 style="font-size:16px">{{rulesTitle}}</h2><p class="sub" style="font-size:12.5px">{{rulesSubtitle}}</p>', RULES_BODY, "", aria="Detection rules")

TECH_BODY = T("""
<div class="row wrap" style="gap:8px;align-items:center;margin-bottom:4px">
  <span class="mono" style="font-weight:600;font-size:15px">{{tId}}</span>
  <span class="chip {{tTone}}">{{tStateLabel}}</span>
  <sc-if value="{{tHasStrength}}" hint-placeholder-val="{{false}}"><span class="chip {{tStrengthTone}} tip" data-tip="Detection strength estimates how well the mapped rules would actually catch this technique (rule provenance, enabled state, and whether the logic references the telemetry the technique expects). It is separate from the coverage % — coverage only says whether a rule exists.">{{tStrengthLabel}} · {{tStrengthScore}}/100</span></sc-if>
</div>
<div class="sub" style="font-size:12.5px;margin-bottom:2px">{{tName}}</div>
<div class="faint" style="font-size:12px;margin-bottom:10px">{{tTactics}}</div>
<sc-if value="{{tHasToolCredit}}" hint-placeholder-val="{{false}}">
<div class="card" style="padding:10px 12px;margin-bottom:12px;background:var(--accent-soft);border-color:#C9D9F5">
  <div style="font-weight:600;font-size:12.5px">Tool credit — MITRE-evaluated</div>
  <p style="font-size:12px;margin-top:4px">{{tToolBlurb}}</p>
  <button class="btn sm" style="margin-top:8px" onClick="{{tToolAttest}}">{{tToolBtn}}</button>
</div>
</sc-if>
<sc-if value="{{tIsNa}}" hint-placeholder-val="{{false}}">
<div class="card" style="padding:10px 12px;margin-bottom:12px;background:var(--na)">
  <div style="font-weight:600;font-size:12.5px">Why this doesn't count toward coverage</div>
  <p style="font-size:12px;margin-top:4px">{{tNaReason}}</p>
</div>
</sc-if>
<div class="stack" style="gap:12px">
  <div><div class="lbl">What is this?</div><p style="font-size:13px">{{tDef}} Attackers use this to {{tUse}}.</p></div>
  <div><div class="lbl">{{tFitLabel}}</div>
    <p style="font-size:13px">This is a <b>{{tTactic1}}</b> technique — {{tFitLine}}.</p>
    <sc-if value="{{tHasVia}}" hint-placeholder-val="{{false}}"><p style="font-size:13px;margin-top:4px">A log source you already collect — <b>{{tVia}}</b> — could see this activity.</p></sc-if>
    <sc-if value="{{tNoVia}}" hint-placeholder-val="{{true}}"><p style="font-size:13px;margin-top:4px">Telemetry: {{tHint}}.</p></sc-if>
    <p class="faint" style="font-size:12px;margin-top:4px">Applies to: {{tPlatforms}}</p>
  </div>
  <div><div class="lbl">{{tWhyLabel}}</div><p style="font-size:13px">{{tWhyText}}</p></div>
  <div><div class="lbl">What would good look like?</div>
    <p style="font-size:13px">{{tGoodText}}</p>
    <sc-if value="{{tHasStarting}}" hint-placeholder-val="{{false}}"><p style="font-size:12.5px;margin-top:4px" class="sub">Starting point: copy your rule '{{tStartRule}}'.</p></sc-if>
  </div>
  <div class="card" style="padding:10px 12px;background:var(--info-soft);border-color:#C6DBEA"><div class="lbl" style="color:var(--info)">Recommendation</div><p style="font-size:13px;margin-top:4px">{{tRec}}</p></div>
  <div>
    <div class="lbl">Detection rules mapped here ({{tMapN}})</div>
    <sc-if value="{{tMapEmpty}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:12.5px;margin-top:6px">None of your uploaded rules map to this technique.</p></sc-if>
    <div class="stack" style="gap:6px;margin-top:6px">
      <sc-for list="{{tMaps}}" as="mp" hint-placeholder-count="2">
        <div class="card" style="padding:8px 10px;box-shadow:none">
          <div class="row between"><b style="font-size:12.5px">{{mp.name}}</b><button class="xbtn tip" data-tip="Remove this mapping — the rule's remaining mappings are kept and coverage is recomputed." aria-label="{{mp.removeAria}}" onClick="{{mp.remove}}">[[xi]]</button></div>
          <div class="faint" style="font-size:11.5px;margin-top:2px">{{mp.enabled}} · {{mp.source}} · <span class="tip" data-tip="How sure the mapping is (1.0 = your own tag)">confidence {{mp.conf}}</span> · {{mp.rationale}}</div>
        </div>
      </sc-for>
    </div>
    <p class="faint" style="font-size:11px;margin-top:6px">Showing mappings from the first 500 rules only.</p>
    <sc-if value="{{tCanEdit}}" hint-placeholder-val="{{true}}">
      <div class="lbl" style="margin-top:10px">Map another rule to this technique</div>
      <div class="row" style="gap:6px;margin-top:4px">
        <select class="select sm" aria-label="Rule to map to this technique" value="{{addRuleSel}}" onChange="{{setAddRule}}" style="min-width:0;flex:1">
          <option value="">Choose a rule…</option>
          <sc-for list="{{addRuleOpts}}" as="ao" hint-placeholder-count="4"><option value="{{ao.name}}">{{ao.name}}</option></sc-for>
        </select>
        <button class="btn sm" onClick="{{addRuleGo}}">Add</button>
      </div>
      <p class="faint" style="font-size:11px;margin-top:4px">The edit is recorded as "Edited by reviewer" and the coverage numbers update immediately.</p>
      <sc-if value="{{addErr}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert">Could not save the mapping change</p></sc-if>
    </sc-if>
    <sc-if value="{{tCannotEdit}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert">Mappings can be edited once the assessment has completed</p></sc-if>
  </div>
</div>
""", xi=icon("x", 13))
TECH_SHEET = sheet("tech", '<span class="mono" style="font-weight:600">Technique details</span>', TECH_BODY,
                    btn("Prev", "", "chevron-left", "sm", attrs='onClick="{{tPrev}}"') + '<span class="num faint" style="font-size:12px">{{tPos}}</span>' + btn("Next", "", "chevron-right", "sm", attrs='onClick="{{tNext}}"'),
                    aria="Technique details")

# ==================================================================== body + props + build
EXTRA_CSS = "<style>@media (max-width:760px){[data-hide-phone]{display:none}} .menu label,.menu button{cursor:pointer}</style>"

PROPS = {"run": {"editor": "enum", "options": ["completed", "running", "failed", "pending"], "default": "completed", "section": "State"}}

BODY = T("""
[[header]]
[[execband]]
[[toolbanner]]
[[uploadcard]]
[[tabbar]]
[[p1]][[p2]][[p3]][[p4]]
[[drill]][[tech]][[rules]][[attest]]
""", header=HEADER, execband=EXEC_BAND, toolbanner=TOOL_BANNER, uploadcard=UPLOAD_CARD, tabbar=TAB_BAR,
    p1=panel("t", "coverage", COVERAGE_TAB), p2=panel("t", "gaps", GAPS_TAB), p3=panel("t", "assumptions", ASSUMPTIONS_TAB), p4=panel("t", "compare", COMPARE_TAB),
    drill=DRILL_SHEET, tech=TECH_SHEET, rules=RULES_SHEET, attest=ATTEST_DLG)

# ==================================================================== VALS
VALS = r"""
const M = Object.assign({ run: 7, playing: false, legend: {}, hideSubs: false, threatGroup: '',
  runsOnSel: {}, detectedViaSel: {}, platformSearch: '', sourceSearch: '', compareWith: '', search: 'credential',
  gapsAll: false, addRuleSel: '', removedMaps: {} }, S.m || {});
const runCompleted = (P.run || 'completed') === 'completed';
const runTweak = P.run || 'completed';

// ---- flatten the matrix into one lookup used by the heatmap, drill panel, search and drawer ----
const effState = (e, run) => { if (e.state === 'na') return 'na'; if (e.state === 'not_covered') return 'not_covered';
  return (e.since <= run) ? e.state : 'not_covered'; };
const ALL_TECH = [];
Object.keys(D.domains).forEach(dk => { const dom = D.domains[dk];
  dom.tactics.forEach(t => { t.cells.forEach(c => {
    ALL_TECH.push({ id: c.id, name: c.name, state: c.state, since: c.since, rule: c.rule, source: c.source,
      tactic: t.name, tacticKey: t.key, domain: dom.name, domainKey: dk, sub: false, subs: (c.subs || []).map(s => s.id) });
    (c.subs || []).forEach(s => ALL_TECH.push({ id: s.id, name: s.name, state: s.state, since: s.since, rule: s.rule,
      source: s.source, tactic: t.name, tacticKey: t.key, domain: dom.name, domainKey: dk, sub: true, subs: [] }));
  }); });
});
const TECH_IX = {}; ALL_TECH.forEach(e => { e.finalEff = effState(e, 7); e.curEff = effState(e, M.run); TECH_IX[e.id] = e; });
const GAPS_IX = {}; D.gaps.forEach(g => GAPS_IX[g.id] = g);
const TOP_GAP_IDS = D.top_gaps.map(g => g.id);
const STATE_COLOR = { covered: 'var(--ok)', partial: 'var(--med)', not_covered: 'var(--crit)', na: 'var(--ink3)' };
const STATE_TONE_CLS = { covered: 'ok', partial: 'med', not_covered: 'crit', na: 'grey' };

// ---- filters shared by the coverage matrix ----
const legendActive = Object.keys(M.legend).filter(k => M.legend[k]);
const groupSel = M.threatGroup;
const groupDef = groupSel ? D.groups.find(g => g.id === groupSel) : null;
const detSel = Object.keys(M.detectedViaSel).filter(k => M.detectedViaSel[k]);
const runsOnSelKeys = Object.keys(M.runsOnSel).filter(k => M.runsOnSel[k]);
const anyFilterActive = legendActive.length > 0 || !!groupSel || detSel.length > 0 || runsOnSelKeys.length > 0;
const dimOf = (e) => {
  if (legendActive.length && legendActive.indexOf(e.curEff) === -1) return true;
  if (groupDef && groupDef.ids.indexOf(e.id) === -1 && e.tactic !== 'Reconnaissance' && e.tactic !== 'Resource Development') return true;
  if (detSel.length && !(e.source && detSel.indexOf(e.source) !== -1)) return true;
  return false;
};
const shownN = ALL_TECH.filter(e => !dimOf(e)).length;

// ---- header ----
const runRows = D.runs.map((r, i) => { const cur = i === 7; const d = Math.round((r.pct - D.runs[7].pct) * 10) / 10;
  return { label: r.date.split(',')[0] + (cur ? ' — this run' : ''), w: cur ? 700 : 400, color: cur ? 'var(--ink3)' : 'var(--ink)',
    date: r.date, pct: r.pct, delta: cur ? '' : ((d >= 0 ? '+' : '') + d + ' vs this'), dcolor: d > 0 ? 'var(--ok)' : d < 0 ? 'var(--crit)' : 'var(--ink3)',
    compare: () => { self.setIn(['m', 'compareWith'], String(i)); self.setIn(['tab', 't'], 'compare'); self.setState({ listbox: null }); } }; });
const expBtn = (key, label, tip) => ({ cls: runCompleted ? '' : 'disabled', tip: runCompleted ? tip : 'Available once the assessment completes.', click: () => {} });
const statusTone = { completed: 'ok', running: 'info', failed: 'crit', pending: 'grey' }[runTweak];
const statusLabel = { completed: 'Completed', running: 'Running', failed: 'Failed', pending: 'Not run yet' }[runTweak];
const h = {
  name: D.header.name, demo: true, statusTone, statusLabel,
  showRuns: runCompleted, runsToggle: self.lbVals('runs').toggle, runsCls: self.lbVals('runs').cls, runsN: D.runs.length, runRows,
  exp: { execpdf: expBtn('execpdf', 'Exec PDF', 'A 1–3 page executive summary — scorecard, top-5 fixes, roadmap and trend. Made for forwarding to leadership.'),
    fullpdf: expBtn('fullpdf', 'Full PDF', 'The complete report: executive summary plus the detailed gap register, coverage tables and appendices.'),
    xlsx: expBtn('xlsx', 'XLSX', 'Full gap register as a spreadsheet — every technique, rule, gap and assumption.'),
    ppt: expBtn('ppt', 'PPT', 'A presentation-ready briefing deck: headline result, coverage chart, detection quality, top fixes and roadmap — for sharing with stakeholders.'),
    nav: expBtn('nav', 'Navigator', "For your technical team: a machine-readable layer file (JSON) to open at attack.mitre.org/navigator — it paints your coverage onto MITRE's official interactive matrix. Not a readable document; use the PDFs for that.") },
  created: D.header.created, running: runTweak === 'running', failed: runTweak === 'failed', pending: runTweak === 'pending',
  metaLine: D.header.project_name + ' · ' + D.header.scope_label + ' · Prepared by ' + D.header.prepared_by + '. ' + D.header.purpose,
  siemLine: 'Rules pulled read-only from Microsoft Sentinel by the automatic schedule · connection "' + D.header.conn_name + '" · workspace ' + D.header.conn_workspace + ' · ' + D.header.created + ' · ' + D.header.conn_rules + ' rules',
};

// ---- executive band ----
const kpiDefs = [
  { key: 'coverage', label: 'Coverage', value: D.domains.enterprise.pct + D.domains.ics.pct + D.domains.mobile.pct ? (Math.round(1000 * D.counts.covered / D.counts.applicable) / 10) + '%' : '0%', color: 'var(--accent)',
    sub: D.counts.covered + ' of ' + D.counts.applicable + ' applicable',
    tip: 'Strict coverage: ' + D.counts.covered + ' of ' + D.counts.applicable + ' applicable techniques have at least one qualifying detection. Weighted coverage (partial counts as half): ' + (Math.round(1000 * (D.counts.covered + D.counts.partial * 0.5) / D.counts.applicable) / 10) + '%. Click to see the techniques behind this number.' },
  { key: 'enterprise', label: 'Enterprise', value: D.domains.enterprise.pct + '%', color: '', sub: D.domains.enterprise.c + ' of ' + D.domains.enterprise.a, tip: 'Enterprise-domain strict coverage. Click to see the techniques behind this number.' },
  { key: 'ics', label: 'ICS / OT', value: D.domains.ics.pct + '%', color: '', sub: D.domains.ics.c + ' of ' + D.domains.ics.a, tip: 'ICS / OT-domain strict coverage. Click to see the techniques behind this number.' },
  { key: 'mobile', label: 'Mobile', value: D.domains.mobile.pct + '%', color: '', sub: D.domains.mobile.c + ' of ' + D.domains.mobile.a, tip: 'Mobile-domain strict coverage. Click to see the techniques behind this number.' },
  { key: 'covered', label: 'Covered', value: String(D.counts.covered), color: 'ok', sub: 'at least one qualifying rule', tip: D.state_tip.covered + ' Click to see the techniques behind this number.' },
  { key: 'partial', label: 'Partial', value: String(D.counts.partial), color: 'med', sub: 'Each row shows why it only counts as half-covered.', tip: D.state_tip.partial + ' Click to see the techniques behind this number.' },
  { key: 'notcovered', label: 'Not covered', value: String(D.counts.not_covered), color: 'crit', sub: 'ranked in Gaps & Roadmap', tip: D.state_tip.not_covered + ' Click to see the techniques behind this number.' },
  { key: 'na', label: 'N/A', value: String(D.counts.na), color: 'grey', sub: 'left out of the denominator', tip: D.state_tip.na + ' Click to see the techniques behind this number.' },
];
const kpiColor = { ok: 'var(--ok)', med: 'var(--med)', crit: 'var(--crit)', grey: 'var(--ink3)', '': 'var(--ink)' };
const kpis = kpiDefs.map(k => ({ label: k.label, value: k.value, color: kpiColor[k.color] || k.color, sub: k.sub, tip: k.tip, open: () => self.openSheet('drill', k.key, 480) }));
const stemPct = Math.round(1000 * D.counts.covered / D.counts.applicable) / 10;
const topGaps = D.top_gaps.map(g => ({ id: g.id, tip: g.name + ' — ' + g.hint, open: () => self.openSheet('tech', g.id, 480) }));

// ---- tool overlay banner ----
const ov = D.tool_overlay;
const attestBusy = self.busy('attest');

// ---- upload summary card ----
const statusDefs = [
  { key: 'tagged_by_you', label: 'tagged by you', tone: 'ok', n: D.rule_status_counts.customer_tagged, tip: 'This mapping comes from the MITRE technique tag in your uploaded file.', mode: 'status:customer_tagged' },
  { key: 'keyword', label: 'keyword-matched', tone: 'blue', n: D.rule_status_counts.keyword_tagged, tip: "The rule's name or logic contains an exact ATT&CK technique name or a well-known attacker tool/command, so it was mapped automatically — no AI involved.", mode: 'status:keyword_tagged' },
  { key: 'ai', label: 'AI-tagged', tone: 'violet', n: D.rule_status_counts.ai_tagged, tip: 'An AI model read the rule and suggested this technique — spot-check before relying on it.', mode: 'status:ai_tagged' },
  { key: 'manual', label: 'reviewer-edited', tone: 'info', n: D.rule_status_counts.manual, tip: 'A reviewer manually set this mapping — it overrides the original tag, and coverage was recomputed from it.', mode: 'status:manual' },
  { key: 'unmapped', label: 'unmapped', tone: 'grey', n: D.rule_status_counts.unmapped, tip: 'Not mapped to any technique.', mode: 'status:unmapped' },
  { key: 'invalid', label: 'invalid tags', tone: 'crit', n: D.rule_status_counts.invalid, tip: 'Tags invalid — treated as untagged.', mode: 'status:invalid' },
];
const statusChips = statusDefs.map(s => ({ tone: s.tone, tip: s.tip, label: s.label, open: () => self.openSheet('rules', s.mode, 480) }))
  .concat([{ tone: 'grey', tip: 'Rules present in the export but turned off — count as partial at best.', label: '3 disabled', open: () => self.openSheet('rules', 'all', 480) }]);
const invRows = [
  { entry: 'IOT Platform devices (105)', sheet: 'Assets', interp: 'no ATT&CK platform mapping — ignored for platform filtering' },
  { entry: 'Mainframe z/OS billing platform', sheet: 'Assets', interp: "no ATT&CK platform mapping — treated as 'platform not in your environment'" },
  { entry: 'Microsoft Exchange Server 2019 (hybrid, 4 nodes)', sheet: 'Assets', interp: 'mapped to Windows + Office Suite' },
  { entry: 'CyberArk credential vault', sheet: 'Crown Jewels', interp: 'no known platform/category match — not used for gap prioritization' },
];
const srcChips = D.log_sources.map(s => ({ name: s.name, label: s.name + ': ' + s.rules + ' rule(s) → ' + s.techs + ' technique(s)', open: () => self.openSheet('rules', 'source:' + encodeURIComponent(s.name), 480) }));

// ---- filter bar ----
const groupOpts = D.groups.map(g => ({ id: g.id, label: g.name + ' (' + g.id + ')' }));
const platformItems = D.platforms.filter(p => !M.platformSearch || p.name.toLowerCase().indexOf(M.platformSearch.toLowerCase()) !== -1)
  .map(p => ({ name: p.name, on: !!M.runsOnSel[p.name], c: p.c, a: p.a, pct: p.pct, toggle: () => { const s = Object.assign({}, M.runsOnSel); s[p.name] = !s[p.name]; self.setIn(['m', 'runsOnSel'], s); } }));
const sourceItems = D.log_sources.filter(s => !M.sourceSearch || s.name.toLowerCase().indexOf(M.sourceSearch.toLowerCase()) !== -1)
  .map(s => ({ name: s.name, on: !!M.detectedViaSel[s.name], n: s.rules, toggle: () => { const sel = Object.assign({}, M.detectedViaSel); sel[s.name] = !sel[s.name]; self.setIn(['m', 'detectedViaSel'], sel); } }));
const lensParts = [];
if (groupDef) lensParts.push('used by **' + groupDef.name + '**');
if (runsOnSelKeys.length) lensParts.push('that can run on **' + runsOnSelKeys.join(', ') + '**');
if (detSel.length) lensParts.push('detected by rules using **' + detSel.join(', ') + '**');
let lensSentence = lensParts.length ? ('Showing techniques ' + lensParts.join(' · ') + ' — counts update to match.') : 'Showing every applicable technique — counts update to match your filters.';
lensSentence += runsOnSelKeys.length ? ' Platform-independent techniques (e.g. Reconnaissance) stay visible.' : (groupDef ? " Group technique lists are MITRE's directly-attributed set — tradecraft via the group's malware and tools may go further." : '');

// ---- legend ----
const lgTip = (key, extra) => D.state_tip[key] + (extra || '') + ' Click to show only these techniques.';
const mkLegend = (key) => ({ p: legendActive.indexOf(key) !== -1 ? 'true' : 'false', op: (legendActive.length === 0 || legendActive.indexOf(key) !== -1) ? 1 : 0.4,
  tip: key === 'covered' ? lgTip('covered', ' Darker green = more rules detect it (1, 2–3, 4+); the lightest shade means coverage rests on a single rule.') : lgTip(key),
  toggle: () => { const l = Object.assign({}, M.legend); l[key] = !l[key]; self.setIn(['m', 'legend'], l); } });

// ---- run timeline ----
const dates = D.runs.map(r => r.date.split(',')[0]);
const runCov = ALL_TECH.filter(e => e.curEff === 'covered').length;
const runApp = ALL_TECH.filter(e => e.curEff !== 'na').length;
const runPct = runApp ? Math.round(1000 * runCov / runApp) / 10 : 0;
const prevCov = ALL_TECH.filter(e => effState(e, Math.max(0, M.run - 1)) === 'covered').length;
const prevPct = runApp ? Math.round(1000 * prevCov / runApp) / 10 : 0;
const runD = Math.round((runPct - prevPct) * 10) / 10;
const ticks = dates.map((dt, i) => ({ tip: 'Run ' + (i + 1) + ' · ' + dt + (i === M.run ? ' (shown)' : ''), bg: i <= M.run ? 'var(--accent)' : 'var(--line2)', scale: i === M.run ? 'scale(1.4)' : 'scale(1)', pick: () => self.setIn(['m', 'run'], i) }));

// ---- coverage matrix (per domain) ----
const cellVM = (entry, depth, badge) => {
  const eff = entry.curEff; const dim = dimOf(entry);
  const tones = { covered: { bg: 'var(--ok)', fg: '#fff' }, partial: { bg: '#F5D879', fg: '#3A2E05' },
    not_covered: { bg: 'var(--crit-soft)', fg: '#8A2A23' }, na: { bg: 'var(--na)', fg: 'var(--ink3)' } }[eff];
  const border = eff === 'not_covered' ? '#F1C2BB' : 'transparent';
  const ruleN = entry.rule ? 1 : 0;
  let tip = entry.id + ' — ' + entry.name + '\n' + D.state_label[eff] + ': ' + D.state_tip[eff] + '. ' + ruleN + ' rule(s) map here.';
  if (entry.subs.length && M.hideSubs) { const c = entry.subs.filter(id => TECH_IX[id].curEff === 'covered').length;
    tip += ' ' + c + ' of ' + entry.subs.length + ' sub-techniques covered (hidden).'; }
  tip += ' Click for details.';
  return { id: entry.id, name: entry.name, bg: tones.bg, fg: tones.fg, border, op: dim ? 0.28 : 1,
    indent: depth ? '16px' : '0px', badge: badge || '', tip, open: () => self.openSheet('tech', entry.id, 480) };
};
const buildDomain = (dk) => {
  const dom = D.domains[dk];
  const tactics = dom.tactics.map(t => {
    const rows = [];
    t.cells.forEach(c => {
      const entry = TECH_IX[c.id];
      let badge = '';
      if (c.subs && c.subs.length && M.hideSubs) { const cn = c.subs.filter(s => TECH_IX[s.id].curEff === 'covered').length; badge = ' (' + cn + '/' + c.subs.length + ')'; }
      rows.push(cellVM(entry, 0, badge));
      if (!M.hideSubs) (c.subs || []).forEach(s => rows.push(cellVM(TECH_IX[s.id], 1, '')));
    });
    return { name: t.name, count: t.c + '/' + t.a,
      tip: t.name + ': ' + t.c + ' covered of ' + t.a + ' applicable (strict ' + (Math.round(1000 * t.c / t.a) / 10) + '%). Click for the list.',
      drill: () => self.openSheet('drill', 'domain:' + dk, 480), rows };
  });
  const domOpen = self.isOpen('dom:' + dk);
  return { key: dk, name: dom.name, c: dom.c, a: dom.a, pct: dom.pct, tactics, ncols: tactics.length,
    open: domOpen, toggle: () => self.toggleOpen('dom:' + dk), toggleAria: (domOpen ? 'Collapse ' : 'Expand ') + dom.name,
    rot: domOpen ? 'rotate(90deg)' : 'none', drill: () => self.openSheet('drill', 'domain:' + dk, 480),
    filterSuffix: anyFilterActive ? ' with current filters' : '' };
};
const domainList = ['enterprise', 'ics', 'mobile'].map(buildDomain);

// ---- gaps & roadmap tab ----
const priMeta = { 1: { label: 'P1 · Critical', color: 'var(--crit)' }, 2: { label: 'P2 · High', color: 'var(--high)' }, 3: { label: 'P3 · Medium', color: 'var(--info)' }, 4: { label: 'Unranked', color: 'var(--ink3)' } };
const feasMeta = { short: { label: 'Build now', color: 'var(--ok)' }, mid: { label: 'Onboard logs first', color: 'var(--info)' }, long: { label: 'New capability', color: 'var(--ink3)' } };
const gapsSource = D.gaps.map((g, i) => { const pm = priMeta[g.pri]; const fm = feasMeta[g.feas];
  return { rank: i + 1, id: g.id, name: g.name, tactic: g.tactic, pri: g.pri,
    priColor: pm.color, priLabel: pm.label, threat: !!g.threat, crown: !!g.crown,
    strengthScore: g.strength ? g.strength[0] : -1, strengthText: g.strength ? (g.strength[0] + ' · ' + g.strength[1]) : '—',
    feasOrder: { short: 0, mid: 1, long: 2 }[g.feas], feasColor: fm.color, feasLabel: fm.label,
    viaLine: g.via ? ('via ' + g.via) : '', rec: g.rec,
    open: () => self.openSheet('tech', g.id, 480) }; });
const gapsSorted = self.sortVals('gaps', gapsSource, [{ key: 'rank' }, { key: 'name' }, { key: 'pri' }, { key: 'strength', get: r => r.strengthScore }, { key: 'feas', get: r => r.feasOrder }], 'rank', 'asc');
const gapsShown = M.gapsAll ? gapsSorted.rows : gapsSorted.rows.slice(0, 6);
const gapsVals = Object.assign({}, gapsSorted, { rows: gapsShown });
const roadmapDefs = [{ key: 'short', label: 'Short term', window: '0–3 months' }, { key: 'mid', label: 'Mid term', window: '3–9 months' }, { key: 'long', label: 'Long term', window: '9–18 months' }];
const roadmap = roadmapDefs.map(r => { const items = D.gaps.filter(g => g.feas === r.key);
  return { label: r.label, window: r.window, count: items.length, narrative: D.roadmap[r.key], hasItems: items.length > 0, empty: items.length === 0,
    items: items.map(g => ({ id: g.id, name: g.name, open: () => self.openSheet('tech', g.id, 480) })) }; });

// ---- assumptions & N/A tab ----
const ruleChipDefs = [
  { key: 'customer_tagged', label: 'tagged by you', tone: 'ok' }, { key: 'keyword_tagged', label: 'keyword-matched (no AI)', tone: 'blue' },
  { key: 'ai_tagged', label: 'AI-tagged', tone: 'violet' }, { key: 'manual', label: 'reviewer-edited', tone: 'info' },
  { key: 'unmapped', label: 'unmapped', tone: 'grey' }, { key: 'invalid', label: 'with invalid tags', tone: 'crit' },
];
const ruleChips = ruleChipDefs.map(rc => ({ tone: rc.tone, label: D.rule_status_counts[rc.key] + ' ' + rc.label, tip: 'Open the rules in this group', open: () => self.openSheet('rules', 'status:' + rc.key, 480) }));
const threatMatches = D.gaps.filter(g => g.threat).length;
const naGroups = D.na_groups.map((ng, gi) => ({ title: ng.title, blurb: ng.blurb, n: ng.items.length,
  drill: () => self.openSheet('drill', 'nagrp:' + gi, 480),
  items: ng.items.map(it => ({ label: it.key + (ng.items.length > 1 ? '' : ''), tip: (ng.title) + ' — click for details', open: () => self.openSheet('tech', it.key, 480) })) }));

// ---- compare tab ----
const cmpIdx = M.compareWith === '' || M.compareWith == null ? null : +M.compareWith;
const cmpOpts = D.runs.map((r, i) => ({ idx: i, label: r.date + ' (' + r.pct + '%)' })).filter(o => o.idx !== 7);
const curRun = D.runs[7];
const cmpBase = cmpIdx != null ? D.runs[cmpIdx] : null;
const deltaOf = (a, b) => Math.round((a - b) * 10) / 10;
let cmpHeader = '', cmpMismatch = false, deltaChips = [], tacticMoves = [], newCov = [], regressed = [], naChanged = [];
if (cmpBase) {
  cmpHeader = curRun.date.split(',')[0] + ' (' + curRun.pct + '%) vs ' + cmpBase.date.split(',')[0] + ' (' + cmpBase.pct + '%)';
  cmpMismatch = curRun.version !== cmpBase.version;
  const wPct = (r) => r === 7 ? (Math.round(1000 * (D.counts.covered + D.counts.partial * 0.5) / D.counts.applicable) / 10) : curRun.pct;
  const dCov = deltaOf(curRun.pct, cmpBase.pct);
  const chip = (label, val, tip, goodUp) => ({ label, tip, value: (val > 0 ? '▲ +' : val < 0 ? '▼ ' : '— ') + Math.abs(val), color: val === 0 ? 'var(--ink3)' : ((val > 0) === goodUp ? 'var(--ok)' : 'var(--crit)') });
  deltaChips = [
    chip('Coverage %', dCov, 'Change in strict coverage percentage since the older run. Up (green) is better.', true),
    chip('Weighted %', Math.round((wPct(7) - wPct(cmpIdx)) * 10) / 10, 'Change in weighted coverage (partial counts as half).', true),
    chip('Covered', ALL_TECH.filter(e => e.finalEff === 'covered').length - ALL_TECH.filter(e => effState(e, cmpIdx) === 'covered').length, 'Change in the number of covered techniques.', true),
    chip('Not covered', ALL_TECH.filter(e => e.finalEff === 'not_covered').length - ALL_TECH.filter(e => effState(e, cmpIdx) === 'not_covered').length, 'Change in the number of uncovered techniques. Down (green) is better.', false),
    chip('N/A', 0, 'Change in not-applicable techniques (environment or exclusion changes).', true),
  ];
  const tacticPct = (t, run) => { const covN = t.cells.filter(c => effState(TECH_IX[c.id], run) === 'covered').length; return Math.round(1000 * covN / t.cells.length) / 10; };
  D.domains.enterprise.tactics.forEach(t => { const a = tacticPct(t, cmpIdx), b = tacticPct(t, 7); const d = Math.round((b - a) * 10) / 10;
    if (d !== 0) tacticMoves.push({ label: t.name + ' ' + (d > 0 ? '▲ +' : '▼ ') + Math.abs(d) + ' pts', tip: 'Enterprise / ' + t.name + ': ' + a + '% → ' + b + '% strict coverage.' }); });
  ALL_TECH.forEach(e => { const was = effState(e, cmpIdx), now = e.finalEff;
    if (was !== 'covered' && now === 'covered') newCov.push({ id: e.id, name: e.name, change: D.state_label[was] + ' → Covered', open: () => self.openSheet('tech', e.id, 480) });
    if (was === 'covered' && now !== 'covered') regressed.push({ id: e.id, name: e.name, change: 'Covered → ' + D.state_label[now], open: () => self.openSheet('tech', e.id, 480) }); });
}
const l1 = { empty: newCov.length === 0, rows: newCov.slice(0, 6) };
const l2 = { empty: regressed.length === 0, rows: regressed.slice(0, 6) };
const l3 = { empty: naChanged.length === 0, rows: naChanged.slice(0, 6) };

// ---- drill-down sheet ----
const drillMode = S.sheets && S.sheets.drill ? S.sheets.drill.id : null;
const drillContent = (mode) => {
  let title = 'All applicable techniques', subtitle = "Matches on technique ID/name, attack stage, platform, threat group, and your rule names — grouped by coverage state. Click any row for the full story.";
  let list = ALL_TECH.slice(); let naRows = null;
  if (!mode) { /* default: whole assessment */ }
  else if (mode === 'enterprise' || mode === 'ics' || mode === 'mobile') { title = D.domains[mode].name + ' techniques'; list = list.filter(e => e.domainKey === mode); }
  else if (mode.indexOf('domain:') === 0) { const dk = mode.slice(7); title = D.domains[dk].name + ' techniques'; list = list.filter(e => e.domainKey === dk); }
  else if (mode === 'covered') { title = 'Covered techniques'; list = list.filter(e => e.finalEff === 'covered'); }
  else if (mode === 'partial') { title = 'Partially covered techniques'; list = list.filter(e => e.finalEff === 'partial'); }
  else if (mode === 'notcovered') { title = 'Not-covered techniques'; list = list.filter(e => e.finalEff === 'not_covered'); }
  else if (mode === 'na') { title = 'Not-applicable techniques'; list = list.filter(e => e.finalEff === 'na'); }
  else if (mode.indexOf('nagrp:') === 0) { const idx = +mode.slice(6); const grp = D.na_groups[idx]; title = grp.title; subtitle = grp.blurb;
    naRows = grp.items.map(it => ({ id: it.key, name: it.reason, color: STATE_COLOR.na, sub: it.reason, open: () => self.openSheet('tech', it.key, 480) })); }
  else if (mode.indexOf('search:') === 0) { const qv = mode.slice(7); const ql = qv.toLowerCase();
    list = list.filter(e => (e.id + ' ' + e.name + ' ' + e.tactic + ' ' + e.domain + ' ' + (e.rule || '') + ' ' + (e.source || '')).toLowerCase().indexOf(ql) !== -1);
    title = '"' + qv + '" — ' + list.length + ' technique(s)'; }
  if (naRows) return { title, subtitle, groups: [{ label: 'N/A', n: naRows.length, rows: naRows }], empty: naRows.length === 0 };
  const order = ['covered', 'partial', 'not_covered', 'na'];
  const groups = order.map(st => { const rows = list.filter(e => e.finalEff === st); return { label: D.state_label[st], n: rows.length,
    rows: rows.map(e => ({ id: e.id, name: e.name, color: STATE_COLOR[st],
      sub: st === 'partial' ? ('— ' + D.state_tip.partial) : D.state_plain[st],
      open: () => self.openSheet('tech', e.id, 480) })) }; }).filter(g => g.n > 0);
  return { title, subtitle, groups, empty: list.length === 0 };
};
const drillC = drillContent(drillMode);

// ---- rules sheet ----
const rulesMode = (S.sheets && S.sheets.rules ? S.sheets.rules.id : null) || 'all';
const buildRules = (mode) => {
  let list = D.rules, title = 'All ' + D.header.conn_rules + ' rules';
  if (mode.indexOf('status:') === 0) { const key = mode.slice(7); list = D.rules.filter(r => r.status === key); title = list.length + ' rule(s) ' + (D.rule_status_label[key] || key); }
  else if (mode.indexOf('source:') === 0) { const src = decodeURIComponent(mode.slice(7)); list = D.rules.filter(r => r.source === src); title = 'What ' + src + ' gives you: ' + list.length + ' rule(s)'; }
  const rows = list.map(r => ({ name: r.name, meta: (D.rule_status_label[r.status] || r.status) + ' · ' + (r.enabled ? 'Enabled' : 'Disabled') + ' · ' + r.source + ' · ' + r.ref,
    hasMaps: r.techs.length > 0, maps: r.techs.map(tm => ({ id: tm[0], sourceLabel: D.rule_status_label[r.status] || 'Tagged', pct: Math.round(tm[2] * 100), rationale: tm[3], open: () => self.openSheet('tech', tm[0], 480) })) }));
  return { rulesTitle: title, rulesSubtitle: 'Rules from your uploaded detection-rule export ' + D.header.conn_name + ' → ' + D.domains.enterprise.name + '/ICS/Mobile mappings.', ruleRows: rows, rulesEmpty: rows.length === 0 };
};
const rulesC = buildRules(rulesMode);

// ---- technique drawer ----
const techId = (S.sheets && S.sheets.tech && S.sheets.tech.id) || (ALL_TECH[0] && ALL_TECH[0].id) || 'T1078';
const SHOWCASE = {
  'T1552.001': { def: 'Adversaries search local file systems for files containing passwords, keys or tokens saved in plaintext.', use: 'harvest credentials left in config files, scripts or notes without ever touching LSASS memory', fit: 'no rule currently reads file-open/file-read events for common credential-file name patterns' },
  'T1219': { def: 'Legitimate remote access or remote-monitoring software used by IT is repurposed by an attacker to keep persistent hands-on-keyboard access.', use: 'blend in with normal remote-support traffic while keeping a channel back into your environment', fit: 'your rules only look for a specific known-bad tool list, not for any unapproved remote-access tool launching' },
  'T1133': { def: 'Adversaries log in through externally-facing remote access services (VPN, Citrix, RDP gateways) using valid or stolen credentials.', use: 'get an initial foothold without deploying any malware at all', fit: 'the VPN concentrator logs are collected but no rule yet correlates logons against your allow-listed ASN ranges' },
  'T1136.001': { def: 'Adversaries create a new local account on a host to keep a login path independent of the account they first compromised.', use: 'keep backup access if the originally compromised account is disabled', fit: 'local account creation events are collected but not yet alerted on outside your change windows' },
  'T1557': { def: 'Adversaries position themselves between two communicating systems to intercept, log or manipulate traffic — including defeating some MFA flows.', use: 'intercept authentication traffic or session tokens on the local network segment', fit: "DHCP/ARP telemetry needed to see rogue gateways or duplicate DHCP servers isn't onboarded yet" },
  'T1078': { def: 'Adversaries obtain and abuse credentials of existing accounts to gain initial access, persistence or elevated access.', use: 'avoid deploying malware by simply logging in like anyone else', fit: 'your impossible-travel rule already correlates sign-in geo and velocity for this', good: 'Rule 12 already covers this well; the Cloud Accounts sub-technique is comparatively weaker (AI-mapped, no MFA context).' },
  'T1003': { def: 'Adversaries dump credential material from the operating system (e.g. LSASS memory) to obtain account hashes or passwords.', use: 'harvest reusable credentials for lateral movement after gaining a foothold', fit: 'your EDR already flags LSASS access from non-system processes', good: 'Rule 1 already covers this; keep the EDR sensor policy from being tuned down.' },
};
const buildTech = (id) => {
  const e = TECH_IX[id]; const g = GAPS_IX[id]; const sc = SHOWCASE[id] || {};
  const name = e ? e.name : (g ? g.name : id);
  const tactic = e ? e.tactic : (g ? g.tactic : '—');
  const domain = e ? e.domain : 'Enterprise';
  const eff = e ? e.finalEff : 'na';
  const toolTool = D.tool_eval[id];
  const strength = g && g.strength ? g.strength : null;
  const via = g ? g.via : (e && e.source ? e.source : null);
  const rule = e ? e.rule : null;
  const def = sc.def || (name + ' is a technique in the ' + tactic + ' tactic of the ATT&CK ' + domain + ' matrix.');
  const use = sc.use || ('carry out ' + tactic.toLowerCase() + '-stage activity as part of a broader intrusion');
  const fitLine = sc.fit || (eff === 'covered' ? 'your rule set already maps to this technique' : eff === 'partial' ? 'only a partial signal reaches this technique today' : 'no rule in your set currently references the telemetry this technique needs');
  const rec = g ? g.rec : (sc.good || ('Review whether an existing log source can be extended to cover ' + name + '.'));
  const whyLabel = (eff === 'covered' || eff === 'partial') ? 'Why this counts as covered' : (eff === 'na' ? 'Why this doesn’t count toward coverage' : 'Why is it a gap?');
  const whyText = eff === 'na' ? D.state_tip.na : (D.state_tip[eff] + (rule ? (' Mapped rule: ' + rule + '.') : ''));
  const goodText = rule ? "Your existing rule already reaches this — keep it enabled and monitored." : (sc.good || ('No curated detection sketch for this technique — ' + (via ? ('your ‘' + via + '’ can provide some of the telemetry it needs.') : 'none of your onboarded log sources matches it yet.')));
  const mapsSrc = [];
  D.rules.forEach(r => r.techs.forEach(tm => { if (tm[0] === id) mapsSrc.push({ ruleName: r.name, enabled: r.enabled, source: r.source, conf: tm[2], rationale: tm[3] }); }));
  const removedForId = M.removedMaps[id] || {};
  const maps = mapsSrc.map((m, i) => Object.assign({}, m, { i })).filter(m => !removedForId[m.i]).map(m => ({ name: m.ruleName, removeAria: 'Remove the ' + id + ' mapping from ' + m.ruleName,
    remove: () => { const rm = Object.assign({}, M.removedMaps); rm[id] = Object.assign({}, rm[id] || {}, {}); rm[id][m.i] = true; self.setIn(['m', 'removedMaps'], rm); },
    enabled: m.enabled ? 'Enabled' : 'Disabled', source: m.source, conf: m.conf.toFixed(2), rationale: m.rationale }));
  const idx = ALL_TECH.findIndex(x => x.id === id);
  const alreadyMapped = {}; maps.forEach(m => { alreadyMapped[m.name] = true; });
  return {
    tId: id, tTone: STATE_TONE_CLS[eff] || 'grey', tStateLabel: D.state_label[eff] || eff,
    tHasStrength: !!strength, tStrengthTone: strength ? (strength[0] >= 75 ? 'ok' : strength[0] >= 45 ? 'med' : 'crit') : '',
    tStrengthLabel: strength ? strength[1] : '', tStrengthScore: strength ? strength[0] : '',
    tName: name, tTactics: tactic + ' · ' + domain,
    tHasToolCredit: !!toolTool, tToolBlurb: toolTool ? (toolTool + ' was evaluated against this technique in MITRE ATT&CK Evaluations (evals.mitre.org). Credit alone never changes the coverage score — attesting the alert path does.') : '',
    tToolAttest: () => self.runBusy('toolattest-' + id, 900),
    tToolBtn: self.busy('toolattest-' + id) ? 'Attesting…' : ('We monitor ' + (toolTool || '') + '’s alerts — count as covered'),
    tIsNa: eff === 'na', tNaReason: eff === 'na' ? D.state_tip.na : '',
    tDef: def, tUse: use,
    tFitLabel: (eff === 'covered' || eff === 'partial') ? 'Where this fits' : 'Where is the gap?',
    tTactic1: tactic, tFitLine: fitLine,
    tHasVia: !!via, tVia: via || '', tNoVia: !via, tHint: 'process, file and network events consistent with this technique',
    tPlatforms: domain === 'Enterprise' ? 'Windows, Linux, macOS, IaaS, SaaS' : (domain === 'Mobile' ? 'Android, iOS' : 'ICS / OT assets'),
    tWhyLabel: whyLabel, tWhyText: whyText,
    tGoodText: goodText, tHasStarting: !!rule, tStartRule: rule || '',
    tRec: rec,
    tMapN: maps.length, tMapEmpty: maps.length === 0, tMaps: maps,
    tCanEdit: runCompleted, tCannotEdit: !runCompleted,
    addRuleSel: M.addRuleSel || '', setAddRule: (ev) => self.setIn(['m', 'addRuleSel'], ev.target.value),
    addRuleOpts: D.rules.filter(r => !alreadyMapped[r.name]).slice(0, 14).map(r => ({ name: r.name })),
    addRuleGo: () => { if (!M.addRuleSel) return; self.setIn(['m', 'addRuleSel'], ''); },
    addErr: false,
    tPos: (idx >= 0 ? (idx + 1) : 1) + ' of ' + ALL_TECH.length,
    tPrev: () => { const ni = idx > 0 ? idx - 1 : ALL_TECH.length - 1; self.openSheet('tech', ALL_TECH[ni].id, 480); },
    tNext: () => { const ni = (idx >= 0 && idx < ALL_TECH.length - 1) ? idx + 1 : 0; self.openSheet('tech', ALL_TECH[ni].id, 480); },
  };
};
const techC = buildTech(techId);

// ---- assemble ----
const groupStats = groupDef ? (() => { const a = groupDef.ids.length; const c = groupDef.ids.filter(id => TECH_IX[id] && TECH_IX[id].finalEff === 'covered').length;
  return c + '/' + a + ' of their techniques covered (' + (a ? Math.round(1000 * c / a) / 10 : 0) + '%) · aka ' + groupDef.aliases; })() : '';
const curTab = (S.tab && S.tab.t) || 'coverage';

return Object.assign({}, {
  h,
  kpis, headline: 'Of the ' + D.counts.applicable + ' techniques that apply to your environment, your rules can detect ' + D.counts.covered + ' (plus ' + D.counts.partial + ' partially)',
  pct: stemPct, topGaps, version: D.header.attack_version, bandRunDate: D.header.created,

  tools: D.tools_label, adjPct: ov.adjusted_pct, extra: ov.extra, combN: ov.rules_n + ov.n, rulesN: ov.rules_n, rulesPct: ov.rules_pct, toolsN: ov.n, toolsPct: ov.tools_pct,
  attestOpen: () => self.openDlg('attest'), attestLabel: self.busy('attest') ? 'Attesting…' : ('Client confirmed — attest all ' + ov.n + ' for ' + ov.tool),
  dlg: { attest: self.dlgVals('attest') },
  attestQ: 'Attest all ' + ov.n + ' credited techniques for ' + ov.tool + '?',
  attestBody: 'This records that your SOC receives and monitors ' + ov.tool + '’s alerts for these techniques, creates one auditable tool-attested rule per technique in your name, and recomputes the coverage score.',
  attestConfirmLabel: self.busy('attest') ? 'Attesting…' : 'Confirm', attestConfirm: () => self.runBusy('attest', 900, () => self.setState({ dlg: null, dlgArg: null })),

  rulesFile: 'acme_sentinel_usecases_v2.xlsx', rulesTotal: D.header.conn_rules, openAllRules: () => self.openSheet('rules', 'all', 480),
  statusChips, invToggle: () => self.toggleOpen('inv'), invRot: self.isOpen('inv') ? 'rotate(90deg)' : 'none', invCount: invRows.length, invOpen: self.isOpen('inv'), invRows,
  envFile: 'acme_environment_v2.xlsx', platformList: D.platforms.map(p => p.name).join(', '), srcToggle: () => self.toggleOpen('src'), srcCount: 29, toolingN: 16, crownN: 7,
  srcOpen: self.isOpen('src'), srcChips,

  t: self.tabVals('t', ['coverage', 'gaps', 'assumptions', 'compare']),
  q: M.search, setQ: (e) => self.setIn(['m', 'search'], e.target.value),
  qKey: (e) => { if (e.key === 'Enter' && M.search.trim().length >= 3) self.openSheet('drill', 'search:' + M.search.trim(), 480); },
  qSearch: () => { if (M.search.trim().length >= 3) self.openSheet('drill', 'search:' + M.search.trim(), 480); },
  tabsShowExport: curTab !== 'compare',

  group: M.threatGroup, setGroup: (e) => self.setIn(['m', 'threatGroup'], e.target.value), groupOpts,
  runsOnToggle: self.lbVals('runson').toggle, runsOnCls: self.lbVals('runson').cls, runsOnSuffix: runsOnSelKeys.length ? (' (' + runsOnSelKeys.length + ')') : '',
  platformSearch: M.platformSearch, setPlatformSearch: (e) => self.setIn(['m', 'platformSearch'], e.target.value), runsOnClear: () => self.setIn(['m', 'runsOnSel'], {}), platformItems,
  detViaToggle: self.lbVals('detvia').toggle, detViaCls: self.lbVals('detvia').cls, detViaSuffix: detSel.length ? (' (' + detSel.length + ')') : '',
  sourceSearch: M.sourceSearch, setSourceSearch: (e) => self.setIn(['m', 'sourceSearch'], e.target.value), detViaClear: () => self.setIn(['m', 'detectedViaSel'], {}), sourceItems,
  hasGroup: !!groupDef, groupStats, downloadShown: () => {}, shownN, lensSentence,

  lgCov: mkLegend('covered'), lgPar: mkLegend('partial'), lgNo: mkLegend('not_covered'), lgNa: mkLegend('na'),
  legendFiltered: legendActive.length > 0, showAll: () => self.setIn(['m', 'legend'], {}),
  hideSubsPressed: M.hideSubs ? 'true' : 'false', toggleHideSubs: () => self.setIn(['m', 'hideSubs'], !M.hideSubs), hideSubsLabel: M.hideSubs ? 'Sub-techniques hidden' : 'Hide sub-techniques',

  runNum: M.run + 1, runPct, runDelta: (runD >= 0 ? '+' : '') + runD + ' pts vs previous run', runDeltaColor: runD > 0 ? 'var(--ok)' : runD < 0 ? 'var(--crit)' : 'var(--ink3)',
  firstDate: dates[0], lastDate: dates[7], run: M.run, onSlide: (e) => self.setIn(['m', 'run'], +e.target.value), ticks,
  togglePlay: () => { if (self._mitreTimer) { clearInterval(self._mitreTimer); self._mitreTimer = null; self.setIn(['m', 'playing'], false); return; }
    self.setIn(['m', 'playing'], true); if (M.run >= 7) self.setIn(['m', 'run'], 0);
    self._mitreTimer = setInterval(() => { const cur = self.state.m.run; if (cur >= 7) { clearInterval(self._mitreTimer); self._mitreTimer = null; self.setIn(['m', 'playing'], false); } else self.setIn(['m', 'run'], cur + 1); }, 700); },
  playLabel: M.playing ? 'Pause' : 'Play timeline',

  domainList,

  aiTone: 'violet', aiTip: 'Recommendation wording was AI-generated (gpt-4o-mini). All numbers come from computed results, never from the AI.', aiLabel: 'AI-written text',
  gaps: gapsVals, hasMore: D.gaps.length > 6, toggleAll: () => self.setIn(['m', 'gapsAll'], !M.gapsAll), showAllLabel: M.gapsAll ? 'Show top 6 only' : ('Show all ' + D.gaps.length + ' gaps'), roadmap,

  ruleChips, threatMatches, assumptions: D.assumptions, assumptionsEmpty: D.assumptions.length === 0, naTotal: D.counts.na, naGroups,

  cmpWith: M.compareWith || '', setCmp: (e) => self.setIn(['m', 'compareWith'], e.target.value), cmpOpts,
  cmpLoading: false, cmpErr: false, cmpEmpty: cmpIdx == null, cmpHas: cmpIdx != null, cmpHeader,
  cmpMismatch, cmpVerA: cmpBase ? cmpBase.version : '', cmpVerB: curRun.version, deltaChips,
  tacticsEmpty: tacticMoves.length === 0, tacticMoves, l1, l2, l3,

  sheets: { drill: self.sheetVals('drill', 480), tech: self.sheetVals('tech', 480), rules: self.sheetVals('rules', 480) },
  drillTitle: drillC.title, drillSubtitle: drillC.subtitle, drillGroups: drillC.groups, drillEmpty: drillC.empty,
}, rulesC, techC);
"""

# ==================================================================== CLICKS + build
DRILL_OPEN = "document.querySelector('aside.sheet[aria-label=\"Technique drill-down\"]').style.transform.startsWith('translateX(0')"
TECH_OPEN = "document.querySelector('aside.sheet[aria-label=\"Technique details\"]').style.transform.startsWith('translateX(0')"
RULES_OPEN = "document.querySelector('aside.sheet[aria-label=\"Detection rules\"]').style.transform.startsWith('translateX(0')"
DLG_OPEN = "Array.from(document.querySelectorAll('.dlg-ov')).some(d => d.style.pointerEvents === 'auto')"
DLG_CLOSED = "Array.from(document.querySelectorAll('.dlg-ov')).every(d => d.style.pointerEvents === 'none')"

CLICKS = [
    {"css": ".kpi.click", "check": DRILL_OPEN, "note": "Open a KPI tile -> DrillDownPanel"},
    {"css": "button[data-tid]", "check": TECH_OPEN, "note": "Open a matrix cell -> TechniqueDrawer (stacks over the drill sheet)"},
    {"text": "tagged by you", "nth": 0, "check": RULES_OPEN, "note": "Open a status chip -> RuleListPanel"},
    {"label": "Past assessment runs", "check": "document.querySelector('[role=\"listbox\"][aria-label=\"Past assessment runs\"]').className.includes('open')"},
    {"css": "button.chip[aria-pressed]", "check": "document.querySelector('button.chip[aria-pressed=\"true\"]') !== null", "note": "Legend toggle filters the matrix"},
    {"text": "Hide sub-techniques", "check": "Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === 'Sub-techniques hidden')"},
    {"text": "Play timeline", "check": "document.querySelector('input[aria-label=\"Run timeline\"]').value !== '7'", "note": "Play advances the run timeline"},
    {"text": "Client confirmed — attest all 15 for Microsoft Defender for Endpoint", "check": DLG_OPEN},
    {"css": ".dlg-ov[style*='pointer-events: auto'] .dlg-f .btn:not(.primary)", "check": DLG_CLOSED},
    {"text": "Gaps & Roadmap", "check": "document.querySelector('.tab.on').textContent.includes('Gaps')"},
    {"text": "Technique", "nth": 0, "check": "Array.from(document.querySelectorAll('.dt .dh > div')).some(d => d.textContent.includes('Technique') && d.getAttribute('aria-sort') !== 'none')", "note": "Sort the gaps table by Technique"},
    {"text": "Assumptions & N/A", "check": "document.querySelector('.tab.on').textContent.includes('Assumptions')"},
    {"text": "Compare", "nth": 0, "check": "document.querySelector('.tab.on').textContent.trim() === 'Compare'"},
    {"label": "Compare with", "check": "true", "note": "Native select — value change isn't click-simulatable, see codereview_list.py precedent"},
    {"label": "Search this assessment", "check": DRILL_OPEN, "note": "Search (preset query 'credential', 3+ chars) opens the drill sheet"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    state = {
        "tab": {"t": "coverage"},
        "expanded": {"dom:enterprise": True},
        "m": {"run": 7, "playing": False, "legend": {}, "hideSubs": False, "threatGroup": "",
              "runsOnSel": {}, "detectedViaSel": {}, "platformSearch": "", "sourceSearch": "",
              "compareWith": "", "search": "credential", "gapsAll": False, "addRuleSel": "", "removedMaps": {}},
    }
    html = screen(stem, app_shell("mitre", BODY, wide=True), VALS, DATA, state, props=PROPS, extra_css=EXTRA_CSS, phone=phone)
    return [(stem, html)]

