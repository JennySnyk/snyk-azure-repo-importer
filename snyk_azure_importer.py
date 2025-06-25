import requests
import sys
from getpass import getpass

# --- Configuration ---
def get_snyk_tenant():
    """Asks the user to select their Snyk tenant."""
    while True:
        tenant = input("Select your Snyk tenant (US/EU): ").strip().upper()
        if tenant == 'US':
            return "https://api.snyk.io"
        elif tenant == 'EU':
            return "https://api.eu.snyk.io"
        else:
            print("Invalid selection. Please enter 'US' or 'EU'.")

def get_user_config():
    """Gets configuration from the user."""
    print("Please enter your Azure DevOps and Snyk details.")
    azure_org_name = input("Enter your Azure DevOps Organization Name (e.g., 'my-org'): ")
    azure_project_name = input("Enter your Azure DevOps Project Name (e.g., 'my-project'): ")
    azure_pat = getpass("Enter your Azure DevOps Personal Access Token (PAT): ")
    snyk_org_id = input("Enter your Snyk Organization ID (e.g., 'a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8'): ")
    snyk_token = getpass("Enter your Snyk API Token: ")
    snyk_api_base_url = get_snyk_tenant()
    
    config = {
        'AZURE_ORG_NAME': azure_org_name,
        'AZURE_PROJECT_NAME': azure_project_name,
        'AZURE_PAT': azure_pat,
        'SNYK_ORG_ID': snyk_org_id,
        'SNYK_TOKEN': snyk_token,
        'SNYK_API_BASE_URL': snyk_api_base_url
    }

    # Validate that no fields are empty
    for key, value in config.items():
        if not value:
            print(f"Error: {key} cannot be empty.")
            sys.exit(1)
            
    return config

def get_snyk_azure_integration_id(config):
    """Gets the Snyk integration ID for Azure Repos."""
    print("Fetching Snyk integration ID for Azure Repos...")
    url = f"{config['SNYK_API_BASE_URL']}/v1/org/{config['SNYK_ORG_ID']}/integrations"
    headers = {
        'Authorization': f"token {config['SNYK_TOKEN']}",
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        integrations = response.json()
        for integration_id, details in integrations.items():
            if details['name'] == 'azure-repos':
                print(f"Found Azure Repos integration with ID: {integration_id}")
                return integration_id
        print("Error: Azure Repos integration not found in Snyk organization.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Snyk integration ID: {e}")
        sys.exit(1)

def get_repos_and_release_branches(config):
    """
    Fetches all repositories and filters for those that have one or more 
    branches matching the 'release/*' pattern.
    Returns a dictionary where keys are repo IDs and values are a dict 
    containing the repo object and a list of their release branches.
    """
    print("\nFetching repositories and their 'release/*' branches from Azure DevOps...")
    repos_with_release_branches = {}
    repos_url = f"https://dev.azure.com/{config['AZURE_ORG_NAME']}/{config['AZURE_PROJECT_NAME']}/_apis/git/repositories?api-version=6.0"
    auth = ('', config['AZURE_PAT'])
    
    try:
        response = requests.get(repos_url, auth=auth)
        response.raise_for_status()
        repos = response.json().get('value', [])
        print(f"Found {len(repos)} repositories. Checking for 'release/*' branches in each...")

        for repo in repos:
            repo_name = repo['name']
            repo_id = repo['id']
            # Note the trailing slash to make it a prefix search for branches under 'release/'
            branch_url = f"https://dev.azure.com/{config['AZURE_ORG_NAME']}/{config['AZURE_PROJECT_NAME']}/_apis/git/repositories/{repo_id}/refs?filter=heads/release/&api-version=6.0"
            branch_response = requests.get(branch_url, auth=auth)
            branch_response.raise_for_status()
            
            branches_data = branch_response.json().get('value', [])
            if branches_data:
                branch_names = [branch['name'].replace('refs/heads/', '') for branch in branches_data]
                print(f"  - Found {len(branch_names)} release branches in '{repo_name}': {', '.join(branch_names)}")
                # Using repo_id as key because dict (repo object) is not hashable
                repos_with_release_branches[repo_id] = {'repo_object': repo, 'branches': branch_names}
            else:
                print(f"  - No 'release/*' branches found in '{repo_name}'. Skipping.")
        
        return repos_with_release_branches
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Azure repos or branches: {e}")
        sys.exit(1)

def import_project_to_snyk(config, integration_id, repo, branch_name):
    """Imports a single repository branch into Snyk."""
    repo_name = repo['name']
    print(f"  - Importing '{repo_name}' (branch: {branch_name})...")
    import_url = f"{config['SNYK_API_BASE_URL']}/v1/org/{config['SNYK_ORG_ID']}/integration/{integration_id}/import"
    headers = {
        'Authorization': f"token {config['SNYK_TOKEN']}",
        'Content-Type': 'application/json'
    }
    payload = {
        "target": {
            "owner": config['AZURE_PROJECT_NAME'],
            "name": repo_name,
            "branch": branch_name
        }
    }
    try:
        response = requests.post(import_url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"    - Successfully started import for '{repo_name}' (branch: {branch_name}).")
        else:
            print(f"    - Failed to import '{repo_name}' (branch: {branch_name}). Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"    - Error importing project to Snyk: {e}")

def main():
    """Main function to run the script."""
    config = get_user_config()
    integration_id = get_snyk_azure_integration_id(config)
    if not integration_id:
        return

    repos_to_import = get_repos_and_release_branches(config)

    if not repos_to_import:
        print("\nNo repositories found with 'release/*' branches. Exiting.")
        return

    print(f"\nFound {len(repos_to_import)} repositories with 'release/*' branches.")
    
    total_branches_to_import = 0
    for repo_id, repo_data in repos_to_import.items():
        repo = repo_data['repo_object']
        branches = repo_data['branches']
        repo_name = repo['name']
        print(f"\nImporting branches for repository: '{repo_name}'")
        total_branches_to_import += len(branches)
        
        for branch in branches:
            import_project_to_snyk(config, integration_id, repo, branch)
    
    print(f"\nScript finished. Attempted to import {total_branches_to_import} branches across {len(repos_to_import)} repositories.")
    print("Check your Snyk organization for import status.")

if __name__ == "__main__":
    main()
