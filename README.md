# Snyk Azure Repos Importer

This script automates the process of importing projects from Azure Repos into Snyk. It finds all repositories that have branches matching the `release/*` pattern (e.g., `release/v1.0`, `release/hotfix`), and then imports all of those matching branches into Snyk for security monitoring.

## Prerequisites

Before running the script, you need the following:

- Python 3 installed.
- The `requests` library, which can be installed via pip:
  ```bash
  pip install requests
  ```
- An Azure DevOps organization and project.
- A Snyk account with an organization set up.

## How to Run

To run the script, execute it using the Python interpreter from the virtual environment:

```bash
venv/bin/python snyk_azure_importer.py
```

The script will prompt you to enter the following information:
- Your Azure DevOps Organization Name (e.g., `my-org`)
- Your Azure DevOps Project Name (e.g., `my-project`)
- Your Azure DevOps Personal Access Token (PAT)
- Your Snyk Organization ID (e.g., `a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8`)
- Your Snyk API Token
- Your Snyk Tenant (US or EU)


The script will then:
1.  Ask for your configuration details.
2.  Fetch the Snyk integration ID for Azure Repos.
3.  Find all repositories in your Azure DevOps project that have one or more branches matching the `release/*` pattern.
4.  For each of those repositories, import all matching `release/*` branches into Snyk.

The script will print its progress to the console. After it finishes, you can check your Snyk organization to see the status of the imported projects.
