                                          #  RMDC Node Down Monitoring Portal

**Introduction:**

The purpose of this document is to describe installation, configuration, and day-to-day operation of the EMEA Node-Down Monitoring Automation.
The automation replaces the manual 3-hour daily review currently performed by the RMDC team by collecting node-state data centrally, applying standardized fault logic, and distributing a consolidated report by email.

Scope:
  •	Region: Overall, All Fleets, (Currently applied for EMEA Regions)
  •	Sites covered: All Live Projects are available for service.
  •	VPN requirement: User must need to connect with Fluence-VPN in order to access and run script manually.
  •	Frequency: Daily – automated run at 00:30 server time. 

Definitions:
  •	Node Current State : Integer reported by each site’s DAS server. 6 = Running (always OK); 5 = Running (OK only for sites listed in STATE5_OK_SITES).
  •	Central Monitoring Host :  Dedicated Linux VM in the RMDC network (hostname :  enst02ts01pr )

System Architecture Working Procedures:

![image](https://github.com/user-attachments/assets/4cdf290c-4913-4c5d-88fc-dfd0452fb605)

This system is designed to capture all required data points in a centralized manner. We use a central server that has access to all global fleet sites (enst02ts01pr, AWS EC2 instance). It employs local applications with an integrated RUST API and uses an authentication token to access resources. A DSC-created script captures information on faulted nodes, which is stored on the same server. To automate this process, we utilize the built-in scheduler service (crontab) of the Linux servers to run daily at specific times. After capturing the data, the python’s mail client, mail service available on the same server sends a copy of the data via email. To access and view the available data efficiently, we implemented a small web application framework (Flask) on port 3001 for local access by all RMDC team members

URL :  http://enst02ts01pr.fluenceenergy.com:3001/

Note: Without Fluence-VPN Access above resources can’t be reachable.
Software that we used:
Backend: 
  •	Python3.6
  •	Web framework: Flask
  •	Send-mail (Package that comes to send mail from Python built in library)
  •	Crontab (Built-in Service avail in Linux server)
Frontend:
  •	Html & CSS: We used Bootstrap5, in order to make it lightweight
Network:
  •	Port 3001 to access it via a browser
Scheduling:
  30 0 * * *   /usr/bin/python3 /home/rmdc/nodedown/node_down_monitoring_emea.py
Fault Logic Summary:
  •	For each site, retrieve each node’s last one minute value of “Node Current State”.
  •	Consider the node UP if every value is in ok_states set.
  •	ok_states = {6} by default.
  •	If site is in STATE5_OK_SITES, then ok_states = {5, 6}.
  •	If any state outside ok_states is observed, the node is listed as Faulted.
Cyber-Security Measures:
	
TLS Encryption in Transit: 
  •	All HTTPS requests to DAS servers made with verify=True once production certificates are installed.
Secrets Management: 
  •	No hard-coded passwords or API tokens in the script.
  •	DAS tokens stored in dasaccess_file_EMEA.csv; file permission 600 owned by user psahoo.admin.
  •	SMTP relay does not require credentials (IP-whitelist).
Least-Privilege Service Account:
  •	Used a less privileged user account to manage and use Cron job and all file ownership under this account.

Contacts:
  •	Script maintenance: Pradeep Sahoo
  •	Operations support: RMDC
How to Access it?
  To access the RMDC- Node-Down Monitoring portal, employees must connect to Fluence-VPN (Fluencesupport vpn). Once     connected, users need to open their browser to access http://enst02ts01pr.fluenceenergy.com:3001/.  If the URL         won't open, you may need VNC-server access. Contact the Global Network team to enable the port.

![image](https://github.com/user-attachments/assets/67ebcc05-7d09-439c-a308-dc8b20c4666e)


![image](https://github.com/user-attachments/assets/9cc5abfe-bc11-4e61-9d95-9d0fca584e74)

Conclusion
The EMEA Node-Down Monitoring Automation delivers a measurable operational and security win for RMDC:
  •	Efficiency – replaces a ~3-hour manual task with an unattended 90-second job, freeing analysts to focus on root-cause and customer communication.
  •	Consistency – applies identical fault logic across all live EMEA sites, eliminating human variance and spreadsheet errors.
  •	Visibility – provides a richly formatted daily email plus archived CSV/HTML for audit and trend analysis.
  •	Security & Compliance – adheres to Fluence Cyber-Security Standard least-privilege execution, encrypted             transport, and formal change management.
  •	Scalability – architecture and codebase already support additional regions; onboarding APAC or Americas requires only population of site lists and tokens.

