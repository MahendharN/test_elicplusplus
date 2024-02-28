import requests
import base64
from fuzzywuzzy import fuzz
import yaml as yaml1
from ruamel.yaml import YAML
import sys

OWNER = "MahendharN"
REPOS = ["test_elicplusplus","test_blizzard","test_elicdp","release_automation_poc"]
ELICPLUSPLUS_REPO = "test_elicplusplus"
BLIZZARD_REPO = "test_blizzard"
ELICDP_REPO = "test_elicdp"
CPLIVE_CHARTS_REPO = "release_automation_poc"
CPLIVE_CHART_BUILD_NOTES_PATH = "./build_notes.yaml"
CPLIVE_CHART_TAGLIST_PATH = "./taglist.yaml"
CPLIVE_CHARTS_RELEASES_PATH = "./releases.yaml"
DICT_PRESENT_TAG_KEY = "present_tag"
DICT_LAST_TAG_KEY = "last_tag"
DICT_TAG_LIST_KEY = "tag_list"
DICT_YAML_LIST_KEY = "yaml_list"

YAML_TAG_LIST_KEY = "Tag List"
SUBCOMPONENTS_RELEASES_DICT = {BLIZZARD_REPO:"sauronDockerImage"
                               ,ELICPLUSPLUS_REPO:"elicplusplusDockerImage",
                               ELICDP_REPO: "unmanagedScteDockerImage"}
class MergeYaml:

    def __init__(self,owner,token):
        self.owner = owner
        self.token = token

        # Fetch CPLive Charts Build Notes
        try:
            with open(CPLIVE_CHART_BUILD_NOTES_PATH, 'r') as file:
                self.final_build_notes = yaml1.safe_load(file)
                self.final_changes_dict = self.convert_changes_list_to_dict(self.final_build_notes["BuildNotes"]["Changes"])
                self.deprecated_features = self.final_build_notes["BuildNotes"]["Deprecated Features"]
                self.dependecies = self.final_build_notes["BuildNotes"]["Dependencies"]
                self.limitations = self.final_build_notes["BuildNotes"]["Limitations"]
                
        except Exception as e:
            print("Error opening build notes file in local path.")
            print(e)
            exit(1)

        # Fetch Present and Last tag from taglist
        try:
            with open(CPLIVE_CHART_TAGLIST_PATH, 'r') as file:
                taglistdict = yaml1.safe_load(file)
                self.last_tag = taglistdict['Tag List'][-2] if len(taglistdict['Tag List']) > 1 else None
                self.present_tag = taglistdict['Tag List'][-1]
        except Exception as e:
            print("Error opening taglist file in local path.")
            print(e)
            exit(1)

        self.merge_dict = self.get_last_and_present_tag_for_subcomponents()
        print(f"Merge Dict updated with last and present tag for each repo. {self.merge_dict}")
        self._get_tag_list_from_subcomponents()
        print(f"Merge Dict updated with tag list for each repo. {self.merge_dict}")
        self._get_yaml_list_from_subcomponents()
        print(f"Merge Dict updated with yaml for each repo. {self.merge_dict}")
        self._merge_yamls_to_final_build_notes()
        print(f"Print Final Yaml {self.final_build_notes}")
        self.__update_into_file(self.final_build_notes)


    def __update_into_file(self, data):
        yaml = YAML()
        yaml.indent(sequence=4, offset=2)
        yaml.default_flow_style = False
        yaml.preserve_quotes = True
        with open(CPLIVE_CHART_BUILD_NOTES_PATH, 'w') as file:
            try:
                yaml.dump(data, file)
            except Exception as e:
                print(f"Unable to dump YAML data in path {CPLIVE_CHART_BUILD_NOTES_PATH}, data {data}, Error {e}")
                return
        print(f"{CPLIVE_CHART_BUILD_NOTES_PATH} created successfully.")

    def convert_changes_list_to_dict(self,list_of_dicts):
        result_dict = {item['JiraID']: item['description'] for item in list_of_dicts}
        return result_dict

    def _merge_yamls_to_final_build_notes(self):
        for _ , dict in self.merge_dict.items():
            for yaml in dict.get(DICT_YAML_LIST_KEY):
                pass
            yaml = self.final_build_notes
            self.deprecated_features += yaml.get("Deprecated Features", [])
            self.dependecies += yaml.get('Dependencies', [])
            self.limitations += yaml.get('Limitations', [])
            for tickets in yaml.get("BuildNotes", {}).get("Changes", []):
                desc = tickets.get("description")
                ticket = tickets.get("JiraID", "")
                if desc is None:
                    desc = ""
                if len(desc) == 0 or (ticket in self.final_changes_dict and len(self.final_changes_dict.get(ticket)) == 0):
                    self.final_changes_dict[ticket] = ""
                elif ticket in self.final_changes_dict:
                    similarity = fuzz.ratio(desc, self.final_changes_dict[ticket])
                    if similarity < 70:
                        if self.final_changes_dict[ticket].endswith("."):
                            self.final_changes_dict[ticket] = f"{self.final_changes_dict[ticket]} {desc}"
                        else:
                            self.final_changes_dict[ticket] = f"{self.final_changes_dict[ticket]}. {desc}"
                    else:
                        self.final_changes_dict[ticket] = desc
                else:
                    self.final_changes_dict[ticket] = desc

        self.final_build_notes["BuildNotes"]["Changes"] = [{"JiraID": k, "description": v} for k, v in self.final_changes_dict.items()]
        self.final_build_notes["BuildNotes"]["Deprecated Features"] = list(set(self.deprecated_features))
        self.final_build_notes["BuildNotes"]["Dependencies"] = list(set(self.dependecies))
        self.final_build_notes["BuildNotes"]["Limitations"] = list(set(self.limitations))
        
    def _get_yaml_list_from_subcomponents(self):
        for repo , dict in self.merge_dict.items():
            yaml_list = []
            for tag in dict.get(DICT_TAG_LIST_KEY):
                yaml = self.retrieve_github_contents(repo,CPLIVE_CHART_BUILD_NOTES_PATH,tag)
                if yaml:
                    yaml_list.append(yaml)
                else:
                    print(f"{CPLIVE_CHART_BUILD_NOTES_PATH} not found for tag {tag} in repo {repo}")
            self.merge_dict[repo][DICT_YAML_LIST_KEY] = yaml_list

    def get_last_and_present_tag_for_subcomponents(self):
        tagdict = {}

        # Read Present Releases yaml
        try:
            with open(CPLIVE_CHARTS_RELEASES_PATH, 'r') as file:
                present_release = yaml1.safe_load(file)
                present_release_images = present_release["dockerImages"]
        except Exception as e:
            print(f"Error opening {CPLIVE_CHARTS_RELEASES_PATH}.")
            print(e)
            exit(1)

        # Read Present Releases yaml
        last_release = None
        try:
            if self.last_tag:
                last_release = self.retrieve_github_contents(CPLIVE_CHARTS_REPO,CPLIVE_CHARTS_RELEASES_PATH,self.last_tag)
                print(f"Release fetched for {self.last_tag}. Release fetched is {last_release}.")
                if last_release:
                    last_release_images = last_release["dockerImages"]
                else:
                    last_release_images = None
            else:
                last_release_images = None
        except Exception as e:
            print(f"Error while getting {CPLIVE_CHARTS_RELEASES_PATH} from tag {self.last_tag}. Release fetched is {last_release}.")
            print(e)
            exit(1)


        # Update present and last tag
        sauron_dict = {}
        sauron_dict[DICT_PRESENT_TAG_KEY] = self._get_tag_from_release_name(present_release_images["sauronDockerImage"])
        sauron_dict[DICT_LAST_TAG_KEY] = self._get_tag_from_release_name(last_release_images["sauronDockerImage"]) if last_release_images else None
        sauron_dict[DICT_TAG_LIST_KEY] = self.retrieve_github_contents(CPLIVE_CHARTS_REPO,CPLIVE_CHARTS_RELEASES_PATH,sauron_dict[DICT_PRESENT_TAG_KEY]) if last_release_images else None

        for repo , release_key_name in SUBCOMPONENTS_RELEASES_DICT.items():
            repo_dict = {}
            repo_dict[DICT_PRESENT_TAG_KEY] = self._get_tag_from_release_name(present_release_images[release_key_name])
            repo_dict[DICT_LAST_TAG_KEY] = self._get_tag_from_release_name(last_release_images[release_key_name]) if last_release_images else None
            tagdict[repo] = repo_dict

        return tagdict
            
    def _get_tag_list_from_subcomponents(self):
        for repo , dict in self.merge_dict.items():
            yaml_taglist = self.retrieve_github_contents(repo,CPLIVE_CHART_TAGLIST_PATH,dict[DICT_PRESENT_TAG_KEY])
            self.merge_dict[repo][DICT_TAG_LIST_KEY] = self._fetch_tag_list_from_tag_list_yaml(yaml_taglist,dict[DICT_LAST_TAG_KEY],dict[DICT_PRESENT_TAG_KEY])


    def _fetch_tag_list_from_tag_list_yaml(self, yaml_tag_list, last_tag, present_tag):
        try:
            tag_list_dict = yaml1.safe_load(yaml_tag_list)
        except Exception as e:
            return []

        tag_list = tag_list_dict[YAML_TAG_LIST_KEY]
        if last_tag not in tag_list and present_tag not in tag_list:
            return []
        elif last_tag not in tag_list:
            return [present_tag]
        elif present_tag not in tag_list:
            return [] 
        else:
            index_a = tag_list.index(last_tag)
            index_b = tag_list.index(present_tag)
            return tag_list[index_a + 1:index_b + 1]

    def _get_tag_from_release_name(self,release_name):
        return release_name.split(":")[-1]
        
    def retrieve_github_contents(self, remote_repo, remote_path, git_tag):
        print(f"Fetching {remote_path} from tag {git_tag} in Repo {remote_repo}")
        url = f"https://api.github.com/repos/{self.owner}/{remote_repo}/contents/{remote_path}?ref={git_tag}"
        auth = ("",self.token)

        response = requests.get(url, auth=auth)
        if response.ok:
            content = response.json()
            print(content)
            if isinstance(content, dict) and "content" in content:
                file_content = content["content"]
                decoded_content = base64.b64decode(file_content).decode("utf-8")
                return decoded_content
            elif isinstance(content, list):
                directory_listing = [item["name"] for item in content]
                return directory_listing
            else:
                print(f"Content is neither list nor dict {content}")
                return None
        else:
            print(f"Failed to fetch {remote_path} from tag {git_tag} in Repo {remote_repo}. Response {response}")
            return None

if __name__ == '__main__':
    OWNER = sys.argv[1].split("/")[0] if len(sys.argv[1].split("/")) > 1 else OWNER
    TOKEN = sys.argv[2]
    merge = MergeYaml(OWNER,TOKEN)