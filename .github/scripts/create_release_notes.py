import sys
import requests
import re
from datetime import datetime
from ruamel.yaml import YAML
import yaml as yaml1
import os
from fuzzywuzzy import fuzz

BUILD_NOTES_FILE_PATH = "./build_notes.yaml"
TAGLIST_FILE_PATH = "./taglist.yaml"
AUTHOR = "ELICPLUSPLUS"

class ReleaseNotesGenerator:
    def __init__(self, base_branch, git_repo, git_token, present_tag):
        self.base_branch = base_branch
        self.last_tag = self.__get_last_tag_from_taglist()
        if self.last_tag is None:
            print(f"No last tag found in path {TAGLIST_FILE_PATH} to generate release notes")
            exit(1)
        self.git_repo = git_repo
        self.git_token = git_token
        self.present_tag = present_tag

        if self.last_tag == self.present_tag:
            print(f"Last tag and Present tag are the same. Last tag: {self.last_tag}, Present Tag: {self.present_tag}. Thus exiting.")
            exit(1)

        # Log initialization details
        print(f"Initialized ReleaseNotesGenerator with the following parameters:")
        print(f"Base branch: {self.base_branch}")
        print(f"Last tag: {self.last_tag}")
        print(f"Git repository: {self.git_repo}")
        print(f"Git token: {self.git_token}")
        print(f"Present tag: {self.present_tag}")

    def __get_last_tag_from_taglist(self):
        """
        Get last tag from taglist.yml
        """
        try:
            with open(TAGLIST_FILE_PATH) as stream:
                data = yaml1.safe_load(stream)
                tags = data.get("Tag List", [])
                latest_tag = tags[-1] if tags else None
                print(f"Last tag read from taglist: {latest_tag}")
                return latest_tag
        except Exception as exc:
                print("Exception while reading taglist to fetch last tag")
                print(exc)
                exit(1)

    def __get_pr_list_from_github_api(self):
        """
        Get a list of PRs using the GitHub API for generating release notes.
        """
        try:
            # Make a POST request to the GitHub API
            pr_list_res = requests.post(
                f"https://api.github.com/repos/{self.git_repo}/releases/generate-notes",
                headers={
                    "Authorization": f"Bearer {self.git_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "tag_name": self.present_tag,
                    "target_commitish": self.base_branch,
                    "previous_tag_name": self.last_tag,
                    "configuration_file_path": ".github/release.yml",
                },
            ).json()
        
            # Extract PR information from the response body
            lines = pr_list_res["body"].splitlines()
            pr_info_list = []

            for line in lines:
                if line.startswith("* "):
                    # Extract PR number from the line
                    pr_number = line.rsplit("/", 1)[1]

                    # Fetch detailed PR information
                    pr_info = requests.get(
                        f"https://api.github.com/repos/{self.git_repo}/pulls/{pr_number}",
                        headers={
                            "Authorization": f"Bearer {self.git_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    ).json()

                    pr_info_list.append(pr_info)

            return pr_info_list
        except Exception as exc:
            print("Exception occurred while fetching PR information from GitHub API:")
            print(exc)
            exit(1)
    
    def __get_list_of_description(self, pr_info_list):
        """
        Get a list of PR descriptions from the PR information list.
        """
        description_list = []
        for pr_info in pr_info_list:
            if "(Build)" in pr_info.get("title"):
                print(f"Skipping PR as it has (Build) in the title. PR {pr_info['html_url']}")
                continue
            description = pr_info.get("body")
            try:
                description = yaml1.safe_load(description)
            except Exception as e:
                print(f"Error while generating YAML for {pr_info.get('html_url')}. Error: {e}")
                description = None
            if not description:
                print(f"Description of {pr_info.get('html_url')} is empty")
                continue
            description_list.append(description)
        return description_list
    
    def generate_release_notes(self):
        pr_list = self.__get_pr_list_from_github_api()
        print("List of PR's fetched from GitHub API")
        print([pr.get("html_url") for pr in pr_list])
        if not pr_list:
            print("No PR found to generate release notes")
            sys.exit(0)
        description_list = self.__get_list_of_description(pr_list)
        if len(description_list) == 0:
            print("Unable to find description to generate release notes as there are no PRs with Tickets found. Please add atlease one ticket.")
            sys.exit(1)
        yaml_data = self.__get_dict_to_update_in_build_notes(description_list)
        self.__update_into_file(yaml_data)

    def generate_taglist(self):
        if os.path.exists(TAGLIST_FILE_PATH):
            with open(TAGLIST_FILE_PATH, "r") as stream:
                try:
                    data = yaml1.safe_load(stream)
                    tags = data.get("Tag List", [])
                except yaml.YAMLError:
                    tags = []
        else:
            tags = []

        tags.append(self.present_tag)
        updated_data = {"Tag List": tags}
        yaml = YAML()
        yaml.indent(sequence=4, offset=2)
        yaml.default_flow_style = False
        yaml.preserve_quotes = True
        with open(TAGLIST_FILE_PATH, "w") as stream:
            try:
                yaml.dump(updated_data, stream)
            except Exception as e:
                print(f"Unable to dump YAML data in path {TAGLIST_FILE_PATH}, data {updated_data}, Error {e}")
                return
        print(f"Tag '{self.present_tag}' added successfully to path {TAGLIST_FILE_PATH}!")


    def __get_dict_to_update_in_build_notes(self, description_list):
        build_dict = {}
        build_dict["Tag"] = self.present_tag
        current_datetime = datetime.now()
        build_dict["Date"] = current_datetime.strftime("%d-%m-%Y")
        build_dict["Author"] = AUTHOR
        jira_dict = {}
        deprecated_features = []
        dependencies = []
        limitations = []
        for description in description_list:
            for tickets in description.get("Tickets", []):
                desc = tickets.get("Description")
                ticket = tickets.get("JiraID", "")
                if desc is None:
                    desc = ""
                if len(desc) == 0 or (ticket in jira_dict and len(jira_dict.get(ticket)) == 0):
                    jira_dict[ticket] = ""
                elif ticket in jira_dict:
                    similarity = fuzz.ratio(desc, jira_dict[ticket])
                    if similarity < 70:
                        if jira_dict[ticket].endswith("."):
                            jira_dict[ticket] = f"{jira_dict[ticket]} {desc}"
                        else:
                            jira_dict[ticket] = f"{jira_dict[ticket]}. {desc}"
                    else:
                        jira_dict[ticket] = desc
                else:
                    jira_dict[ticket] = desc
            dependencies += description.get("Dependencies", [])
            deprecated_features += description.get("Deprecated Features", [])
            limitations += description.get("Limitations", [])
        jira_list = [{"JiraID": k, "description": v} for k, v in jira_dict.items()]
        if len(jira_list) != 0:
            build_dict["Changes"] = jira_list
        else:
            print("There are no Jira Tickets in the build notes. There has to be atlease one ticket to create release.")
            exit(1)
        if len(dependencies) != 0:
            build_dict["Dependencies"] = list(set(dependencies))
        if len(limitations) != 0:
            build_dict["Limitations"] = list(set(limitations))
        if len(deprecated_features) != 0:
            build_dict["Deprecated Features"] = list(set(deprecated_features))
        return {"BuildNotes": build_dict}

    
    def __update_into_file(self, data):
        yaml = YAML()
        yaml.indent(sequence=4, offset=2)
        yaml.default_flow_style = False
        yaml.preserve_quotes = True
        with open(BUILD_NOTES_FILE_PATH, 'w') as file:
            try:
                yaml.dump(data, file)
            except Exception as e:
                print(f"Unable to dump YAML data in path {BUILD_NOTES_FILE_PATH}, data {data}, Error {e}")
                return
        print(f"{BUILD_NOTES_FILE_PATH} created successfully.")

if __name__ == "__main__":
    base_branch = sys.argv[1]
    git_repo = sys.argv[2]
    git_token = sys.argv[3]
    present_tag = sys.argv[4]
    if base_branch != "develop" and (not base_branch.endswith(".x")) and (not base_branch.startswith("rc")):
        print("Generate Release Notes Workflow is only applicable for .x, develop, and rc branches")
        sys.exit(1)

    release_notes_obj = ReleaseNotesGenerator(base_branch, git_repo, git_token, present_tag)
    release_notes_obj.generate_release_notes()
    release_notes_obj.generate_taglist()
