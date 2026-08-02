# Claude Review Prompt – MITRE ATT&CK Assessment Data Collection Review

## Role
Act as a senior MITRE ATT&CK consultant, SOC architect, SIEM engineer, threat hunter, detection engineer, and Big-4 cybersecurity assessor.

Your objective is to review the data-collection module of my MITRE ATT&CK assessment application and determine whether it collects the minimum amount of information required to perform a comprehensive, accurate, and auditable assessment while keeping the burden on the customer as low as possible.

Do not redesign the entire application from scratch.

Your task is to critically review the existing design and identify:
- Missing information
- Unnecessary information
- Duplicate information
- Overly technical questions
- Questions customers are unlikely to answer
- Data that could be imported automatically
- Better methods of collecting evidence
- Improvements to the user experience
- Improvements to ATT&CK mapping accuracy

## Core principles

### Minimize customer effort
Customers should provide:
- CMDB export
- Asset inventory
- SIEM connector inventory
- Detection-rule inventory
- Architecture diagrams
- Network diagrams
- Sample logs
- Existing ATT&CK mappings
- Exception register

### Assess data sources instead of products
Infoblox SSH logs → Linux mapping
Infoblox DNS logs → Network mapping
Infoblox audit logs → Identity mapping
Infoblox API logs → Application mapping

### Assess the following layers
- Asset coverage
- Log-source coverage
- Parser coverage
- Normalization coverage
- Detection coverage
- ATT&CK coverage

### Supported technologies
- Windows
- Linux
- macOS
- Active Directory
- Entra ID
- Okta
- AWS
- Azure
- GCP
- Kubernetes
- Firewalls
- Proxies
- IDS/IPS
- DNS appliances
- Backup appliances
- Email gateways
- EDR platforms
- Mainframes
- SaaS platforms
- Custom applications

## Special appliance handling
Infoblox:
- SSH logs
- Syslog
- DNS logs
- DHCP logs
- IPAM logs
- Audit logs

Rubrik:
- Backup logs
- Audit logs
- Administrative logs
- API logs

VMware Photon OS:
- Authentication logs
- Process logs
- Audit logs

z/OS:
- SMF records
- RACF logs
- Custom mappings

## Review criteria
For every field determine:
- Is it required?
- Why is it required?
- Can it be collected automatically?
- Can customers easily provide it?
- Does it improve ATT&CK coverage quality?

## Expected output
1. Executive summary.
2. Required fields.
3. Optional fields.
4. Fields to remove.
5. Workflow recommendations.
6. Final scoring.

Be extremely critical and optimize for completeness, usability, automation, and accuracy.
