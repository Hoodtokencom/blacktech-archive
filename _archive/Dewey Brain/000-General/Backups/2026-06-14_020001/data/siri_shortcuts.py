# Siri Shortcuts for Blacktech Solutions
# =========================================
# These are webhook URLs your iPhone/iPad Siri Shortcuts call.
# Each one hits your Command Center API on the Pi.
#
# HOW TO SET UP (takes 2 minutes per shortcut):
#   1. Open "Shortcuts" app on iPhone
#   2. Tap "+" to create new shortcut
#   3. Add action: "Get Contents of URL"
#   4. Set the URL below, Method = GET or POST
#   5. Tap the shortcut name → "Add to Siri"
#   6. Record your voice phrase
#
# BASE URL: https://app.blacktechsolutionscorp.com
# =========================================

SHORTCUTS = [
    {
        "name": "Finance Report",
        "phrase": "Hey Siri, Business report",
        "url": "https://app.blacktechsolutionscorp.com/api/weekly-report-now",
        "method": "GET",
        "description": "Triggers weekly finance report and sends it to Telegram right now"
    },
    {
        "name": "Tax Estimate",
        "phrase": "Hey Siri, What do I owe in taxes",
        "url": "https://app.blacktechsolutionscorp.com/api/tax-estimate",
        "method": "GET",
        "description": "Returns current quarterly tax estimate"
    },
    {
        "name": "Commissions",
        "phrase": "Hey Siri, Check my commissions",
        "url": "https://app.blacktechsolutionscorp.com/api/commissions",
        "method": "GET",
        "description": "Returns Think Energy commission dashboard"
    },
    {
        "name": "Job Status",
        "phrase": "Hey Siri, Job status",
        "url": "https://app.blacktechsolutionscorp.com/api/jobs-summary",
        "method": "GET",
        "description": "Returns count of active, invoiced, and lead jobs"
    },
    {
        "name": "Payment Summary",
        "phrase": "Hey Siri, Payment summary",
        "url": "https://app.blacktechsolutionscorp.com/api/payments/summary",
        "method": "GET",
        "description": "Returns total invoiced vs collected vs overdue"
    },
    {
        "name": "Add Lead",
        "phrase": "Hey Siri, Add a lead",
        "url": "https://app.blacktechsolutionscorp.com/api/leads/quick",
        "method": "POST",
        "body": {"name": "{{Name}}", "source": "siri", "phone": "{{Phone}}"},
        "description": "Adds a quick lead — you fill in name + phone via Shortcut prompt"
    },
    {
        "name": "Gusto Status",
        "phrase": "Hey Siri, Payroll status",
        "url": "https://app.blacktechsolutionscorp.com/api/gusto-status",
        "method": "GET",
        "description": "Returns Gusto payroll connection status"
    },
    {
        "name": "System Health",
        "phrase": "Hey Siri, System check",
        "url": "https://app.blacktechsolutionscorp.com/api/health",
        "method": "GET",
        "description": "Returns all 8 service statuses"
    },
]
