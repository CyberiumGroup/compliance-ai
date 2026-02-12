# Information Security Policy

**Effective Date:** January 1, 2025
**Last Reviewed:** January 1, 2026
**Owner:** Chief Information Security Officer (CISO)
**Classification:** Internal

## 1. Purpose

This policy establishes the information security requirements for protecting the confidentiality, integrity, and availability of company information assets. It applies to all employees, contractors, and third parties with access to company systems and data.

## 2. Scope

This policy covers all information assets owned or managed by the organization, including but not limited to: electronic data, physical records, IT infrastructure, cloud services, and third-party systems processing company data.

## 3. Information Classification

All information must be classified according to the following scheme:

- **Restricted:** Information whose unauthorized disclosure would cause severe harm. Examples: encryption keys, authentication credentials, financial records.
- **Confidential:** Business-sensitive information with limited distribution. Examples: customer PII, employee records, strategic plans.
- **Internal:** Information intended for internal use only. Examples: internal communications, process documentation.
- **Public:** Information approved for public distribution. Examples: marketing materials, published reports.

Handling requirements, including storage, transmission, and disposal procedures, are defined for each classification level in the Data Handling Standards document.

## 4. Access Control

### 4.1 Authentication
All access to company systems requires individual user accounts. Shared accounts are prohibited except where technically necessary and approved by the CISO. Multi-factor authentication (MFA) is required for all remote access, administrative accounts, and access to systems processing Confidential or Restricted data.

### 4.2 Authorization
Access rights are granted based on the principle of least privilege and must be tied to a documented business need. Role-based access control (RBAC) is the standard authorization model. Access reviews are conducted quarterly by system owners.

### 4.3 Account Management
User accounts must be provisioned through the IT ticketing system with manager approval. Accounts are disabled within 24 hours of employment termination. Accounts inactive for 90 days are automatically disabled.

## 5. Network Security

### 5.1 Network Architecture
Production environments must be segmented from corporate and development networks. Network segmentation is enforced through firewalls and virtual LANs. All inter-segment traffic must be explicitly permitted through documented firewall rules.

### 5.2 Remote Access
Remote access to the corporate network is permitted only through the approved VPN solution with MFA. Split tunneling is disabled on VPN connections. All remote access sessions are logged.

### 5.3 Wireless Security
Corporate wireless networks use WPA3 encryption and 802.1X authentication. Guest wireless networks are isolated from the corporate network and provide internet access only.

## 6. Data Protection

### 6.1 Encryption
Data classified as Confidential or Restricted must be encrypted in transit using TLS 1.2 or higher and at rest using AES-256. Encryption keys are managed through the enterprise key management system with annual key rotation.

### 6.2 Data Loss Prevention
DLP controls are implemented at email gateways, web proxies, and endpoints to prevent unauthorized transmission of classified data. DLP alerts are reviewed daily by the security team.

### 6.3 Data Retention and Disposal
Data is retained in accordance with the Data Retention Schedule. When no longer required, electronic data must be securely erased using approved sanitization methods. Physical media must be shredded or degaussed.

## 7. Incident Response

### 7.1 Reporting
All employees must report suspected security incidents immediately through the security incident hotline or email. Failure to report known incidents may result in disciplinary action.

### 7.2 Response Process
The Security Operations team triages all reported incidents and classifies them by severity. Critical incidents trigger the Incident Response Team activation with defined escalation paths to executive leadership and legal counsel.

### 7.3 Post-Incident Review
All significant incidents undergo a post-incident review within 14 days of resolution. Lessons learned are documented and shared with relevant stakeholders. Remediation actions are tracked to completion.

## 8. Business Continuity

### 8.1 Backup
Critical systems are backed up daily (incremental) and weekly (full). Backups are stored in a geographically separate location. Backup integrity is verified monthly.

### 8.2 Disaster Recovery
Disaster recovery plans are maintained for all critical systems with defined Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO). DR plans are tested annually through simulation exercises.

## 9. Third-Party Security

Vendors and partners with access to company systems or data must meet minimum security requirements as defined in the Third-Party Security Standards. This includes annual security assessments, contractual security obligations, and right-to-audit clauses.

## 10. Compliance

Compliance with this policy is mandatory. Violations may result in disciplinary action up to and including termination of employment or contract. The security team conducts periodic audits to verify compliance.
