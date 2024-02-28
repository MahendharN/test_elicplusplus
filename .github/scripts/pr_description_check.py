import os
import json
import re
import yaml

def check_jira_format(string):
    """Check if a string follows the format 'ABC-123'."""
    pattern = r'^[A-Z]+-\d+$'
    return re.match(pattern, string) is not None

def read_yaml(file_path):
    """Read YAML data from a file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)
    
def main():
    # Load pull request event payload
    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_payload = json.load(f)

    title = event_payload['pull_request']['title']
    title_pattern = "(Build)"

    # Skip description check if title contains 'Build'
    if title_pattern in title:
        print("Title starts with 'Build', skipping description check.")
        exit(0)

    description = event_payload['pull_request']['body']
    if description is None:
        print("PR Description is None")
        print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
        exit(1)

    try:
        parsed_data = yaml.safe_load(description)
    except Exception as e:
        print(description)
        print("Unable to generate YAML as description is wrong")
        print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
        exit(1)


    if parsed_data is None or parsed_data == {}:
        print("No YAML Description Provided")
        print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
        exit(1)

    # Print the parsed data
    main_keys = ["Tickets","Dependencies","Deprecated Features","Limitations"]
    if not any(key in parsed_data.keys() for key in main_keys):
        print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
        exit(1)

    # Ticket Field Check  
    required_tickets_keys = ['JiraID', 'Description', 'SubTickets']
    if "Tickets" in parsed_data:
        for entry in parsed_data['Tickets']:
            missing_keys = [key for key in required_tickets_keys if key not in entry]
            # If any key is missing raise error
            if missing_keys:
                print(f"Error: Missing required keys in 'Tickets' entry: {', '.join(missing_keys)}")
                print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
                exit(1)
            # If SubTickets is not list raise error
            if not isinstance(entry['SubTickets'], list):
                print("Error: 'SubTickets' must be a list.")
                print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
                exit(1)
            # If JiraID is not string and not in format CRP-1292 raise error
            if type(entry["JiraID"]) is not str or not check_jira_format(entry["JiraID"]):
                print("Error: 'JiraID' must be formatted as 'CRP-123'")
                print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
                exit(1)
            # If SubTickets is not string and not in format CRP-1292 raise error
            for sub_ticket in entry['SubTickets']:
                if type(sub_ticket) is not str or not check_jira_format(sub_ticket):
                    print("Error: 'SubTickets' must be formatted as 'CRP-123'")
                    print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
                    exit(1)
        
    # Dependencies Field Check
    optional_keys = ['Deprecated Features', 'Dependencies', 'Limitations']
    for key in optional_keys:
        if key in parsed_data:
            # If optionals are not a list raise error
            if not isinstance(parsed_data[key], list):
                print(f"Error: '{key}' must have a list value.")
                print("PR Description is not Valid. Please check the link https://amagiengg.atlassian.net/wiki/spaces/CLOUD/pages/3408199746/ES+CRP-1292+Automate+Build+Note+Genration+for+Cloudport+applications to check the required format.")
                exit(1)

    print("PR Description is valid.")

if __name__ == "__main__":
    main()
